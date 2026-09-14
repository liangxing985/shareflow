"""订单路由（含API接入）"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
from app.database import get_db
from app.models.user import User
from app.models.order import Order
from app.models.share_record import ShareRecord
from app.models.share_rule import ShareRule
from app.schemas.order import OrderCreate, OrderApiCreate, OrderUpdate, OrderResponse, OrderDetailResponse, OrderListRequest
from app.schemas.common import PageResponse
from app.dependencies import get_current_user
from app.services.share_service import ShareEngine
from app.core.audit_log import log_operation
from app.config import settings

router = APIRouter(prefix="/orders", tags=["订单管理"])


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """API Key鉴权依赖"""
    if not settings.api_keys_list:
        raise HTTPException(status_code=500, detail="系统未配置API_KEYS，请联系管理员")
    if not x_api_key or x_api_key not in settings.api_keys_list:
        raise HTTPException(status_code=401, detail="无效的API Key")
    return x_api_key


def generate_order_no() -> str:
    """生成订单号"""
    return f"SF{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


@router.get("", response_model=PageResponse[OrderResponse])
async def list_orders(
    page: int = 1, page_size: int = 20,
    keyword: str = None, category: str = None,
    share_status: str = None, pay_status: str = None, source: str = None,
    start_date: str = None, end_date: str = None,
    min_amount: Decimal = None, max_amount: Decimal = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """订单列表"""
    query = select(Order)
    count_query = select(func.count(Order.id))

    if keyword:
        condition = or_(Order.order_no.contains(keyword), Order.out_order_no.contains(keyword),
                        Order.payer_name.contains(keyword), Order.product_name.contains(keyword))
        query = query.where(condition)
        count_query = count_query.where(condition)
    if category:
        query = query.where(Order.category == category)
        count_query = count_query.where(Order.category == category)
    if share_status:
        query = query.where(Order.share_status == share_status)
        count_query = count_query.where(Order.share_status == share_status)
    if pay_status:
        query = query.where(Order.pay_status == pay_status)
        count_query = count_query.where(Order.pay_status == pay_status)
    if source:
        query = query.where(Order.source == source)
        count_query = count_query.where(Order.source == source)
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        query = query.where(Order.created_at >= start)
        count_query = count_query.where(Order.created_at >= start)
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        query = query.where(Order.created_at < end)
        count_query = count_query.where(Order.created_at < end)
    if min_amount:
        query = query.where(Order.total_amount >= min_amount)
        count_query = count_query.where(Order.total_amount >= min_amount)
    if max_amount:
        query = query.where(Order.total_amount <= max_amount)
        count_query = count_query.where(Order.total_amount <= max_amount)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size)
    orders = (await db.execute(query)).scalars().all()

    return PageResponse(items=orders, total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size)


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """订单详情（含分账明细）"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 查分账明细
    records_result = await db.execute(select(ShareRecord).where(ShareRecord.order_id == order_id).order_by(ShareRecord.level, ShareRecord.id))
    records = records_result.scalars().all()

    order_dict = OrderResponse.model_validate(order).model_dump()
    order_dict["share_records"] = [
        {
            "id": r.id,
            "shareholder_id": r.shareholder_id,
            "shareholder_name": r.shareholder_name,
            "share_rate": float(r.share_rate) if r.share_rate else None,
            "share_amount": float(r.share_amount),
            "actual_amount": float(r.actual_amount) if r.actual_amount else None,
            "level": r.level,
            "parent_shareholder_id": r.parent_shareholder_id,
            "status": r.status,
        }
        for r in records
    ]
    return order_dict


@router.post("", response_model=OrderResponse)
async def create_order(
    req: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """手动创建订单"""
    order_no = req.order_no or generate_order_no()

    # 检查订单号重复
    exist = await db.execute(select(Order).where(Order.order_no == order_no))
    if exist.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="订单号已存在")

    order = Order(
        order_no=order_no,
        out_order_no=req.out_order_no,
        total_amount=req.total_amount,
        payment_account_id=req.payment_account_id,
        payer_name=req.payer_name,
        payer_contact=req.payer_contact,
        product_name=req.product_name,
        product_desc=req.product_desc,
        category=req.category,
        share_rule_id=req.share_rule_id,
        paid_at=req.paid_at or datetime.now(timezone.utc),
        transaction_id=req.transaction_id,
        remark=req.remark,
        source="manual",
        created_by=current_user.id,
    )
    db.add(order)
    await db.flush()

    # 自动分账
    if req.auto_share:
        rule = await ShareEngine.get_applicable_rule(db, order)
        if rule:
            await ShareEngine.execute_share(db, order, rule, current_user.id)
        else:
            order.share_status = "skipped"

    await db.commit()
    await db.refresh(order)
    return order


@router.post("/api/create", response_model=OrderResponse)
async def api_create_order(
    req: OrderApiCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """API接入创建订单（需X-API-Key鉴权）"""
    client_ip = request.client.host if request.client else ""

    # 检查外部订单号重复
    exist = await db.execute(select(Order).where(Order.out_order_no == req.out_order_no))
    if exist.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="外部订单号已存在")

    order = Order(
        order_no=generate_order_no(),
        out_order_no=req.out_order_no,
        total_amount=req.total_amount,
        payer_name=req.payer_name,
        payer_contact=req.payer_contact,
        product_name=req.product_name,
        product_desc=req.product_desc,
        category=req.category,
        share_rule_id=req.share_rule_id,
        paid_at=datetime.now(timezone.utc),
        remark=req.remark,
        source="api",
    )
    db.add(order)
    await db.flush()

    if req.auto_share:
        rule = await ShareEngine.get_applicable_rule(db, order)
        if rule:
            await ShareEngine.execute_share(db, order, rule)
        else:
            order.share_status = "skipped"

    await log_operation(db, None, "api_create_order", "order", order.id,
                         f"API创建订单 {order.order_no}，金额 {order.total_amount}，IP: {client_ip}", client_ip)
    await db.commit()
    await db.refresh(order)
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int, req: OrderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新订单"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)

    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/reshare")
async def reshare_order(
    order_id: int,
    share_rule_id: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """重新分账（先撤销原分账再重新分账）"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查是否有已结算的分账明细
    records_result = await db.execute(
        select(ShareRecord).where(ShareRecord.order_id == order_id, ShareRecord.status.in_(["settled", "settling"]))
    )
    if records_result.scalars().first():
        raise HTTPException(status_code=400, detail="存在已结算或结算中的分账明细，无法重新分账")

    # 删除原分账明细，回滚余额
    old_records = (await db.execute(select(ShareRecord).where(ShareRecord.order_id == order_id))).scalars().all()
    for record in old_records:
        balance_result = await db.execute(select(__import__("app.models.share_balance", fromlist=["ShareBalance"]).ShareBalance).where(__import__("app.models.share_balance", fromlist=["ShareBalance"]).ShareBalance.shareholder_id == record.shareholder_id))
        balance = balance_result.scalar_one_or_none()
        if balance:
            from app.services.share_service import to_decimal
            balance.total_receivable = to_decimal(balance.total_receivable) - to_decimal(record.share_amount)
            balance.current_balance = to_decimal(balance.current_balance) - to_decimal(record.share_amount)
            balance.total_orders = max(0, (balance.total_orders or 0) - 1)
        await db.delete(record)

    # 重新分账
    if share_rule_id:
        order.share_rule_id = share_rule_id
    order.share_status = "pending"
    order.platform_fee = None
    order.shareable_amount = None

    rule = await ShareEngine.get_applicable_rule(db, order)
    if rule:
        await ShareEngine.execute_share(db, order, rule, current_user.id)
    else:
        order.share_status = "skipped"

    await db.commit()
    return {"success": True, "message": "重新分账完成"}


@router.get("/stats/summary")
async def order_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """订单统计概览"""
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar()
    total_amount = (await db.execute(select(func.coalesce(func.sum(Order.total_amount), 0)))).scalar()
    total_platform_fee = (await db.execute(select(func.coalesce(func.sum(Order.platform_fee), 0)))).scalar()
    shared_orders = (await db.execute(select(func.count(Order.id)).where(Order.share_status == "done"))).scalar()

    # 今日统计
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = (await db.execute(select(func.count(Order.id)).where(Order.created_at >= today_start))).scalar()
    today_amount = (await db.execute(select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.created_at >= today_start))).scalar()

    return {
        "total_orders": total_orders,
        "total_amount": float(total_amount),
        "total_platform_fee": float(total_platform_fee),
        "shared_orders": shared_orders,
        "today_orders": today_orders,
        "today_amount": float(today_amount),
    }
