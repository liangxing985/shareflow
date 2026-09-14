"""订单路由（含API接入）"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
from loguru import logger
from app.database import get_db
from app.models.user import User
from app.models.order import Order
from app.models.share_record import ShareRecord
from app.models.share_rule import ShareRule
from app.schemas.order import OrderCreate, OrderApiCreate, OrderUpdate, OrderResponse, OrderDetailResponse, OrderListRequest, AdminConfirmRequest
from app.schemas.common import PageResponse
from app.dependencies import get_current_user
from app.services.share_service import ShareEngine
from app.services.notify_service import notify_service
from app.services.system_config_service import system_config_service
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
    """手动创建订单（默认已支付，可设置为待支付）"""
    order_no = req.order_no or generate_order_no()

    # 检查订单号重复
    exist = await db.execute(select(Order).where(Order.order_no == order_no))
    if exist.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="订单号已存在")

    # 判断是否待支付：如果传了paid_at则视为已支付，否则待支付
    is_paid = req.paid_at is not None or req.auto_share
    pay_status = "paid" if is_paid else "pending_pay"
    pay_expire_at = None
    if not is_paid:
        pay_expire_at = datetime.now(timezone.utc) + timedelta(minutes=5)

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
        pay_status=pay_status,
        paid_at=req.paid_at or (datetime.now(timezone.utc) if is_paid else None),
        pay_expire_at=pay_expire_at,
        transaction_id=req.transaction_id,
        remark=req.remark,
        source="manual",
        created_by=current_user.id,
    )
    db.add(order)
    await db.flush()

    # 自动分账（仅已支付订单）
    if req.auto_share and is_paid:
        rule = await ShareEngine.get_applicable_rule(db, order)
        if rule:
            await ShareEngine.execute_share(db, order, rule, current_user.id)
        else:
            order.share_status = "skipped"

    await db.commit()
    await db.refresh(order)

    # 构造返回，添加pay_url
    result = OrderResponse.model_validate(order).model_dump()
    if pay_status == "pending_pay":
        result["pay_url"] = f"/pay/{order.order_no}"
    return result


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

    # API创建的订单默认为待支付状态，设置5分钟过期
    pay_expire_at = datetime.now(timezone.utc) + timedelta(minutes=5)

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
        pay_status="pending_pay",
        pay_expire_at=pay_expire_at,
        remark=req.remark,
        source="api",
    )
    db.add(order)
    await db.flush()

    # API创建的订单默认不自动分账，等确认收款后再分账
    if req.auto_share:
        # 如果显式要求自动分账，则标记为已支付并分账
        order.pay_status = "paid"
        order.paid_at = datetime.now(timezone.utc)
        order.pay_expire_at = None
        rule = await ShareEngine.get_applicable_rule(db, order)
        if rule:
            await ShareEngine.execute_share(db, order, rule)
        else:
            order.share_status = "skipped"

    await log_operation(db, None, "api_create_order", "order", order.id,
                         f"API创建订单 {order.order_no}，金额 {order.total_amount}，IP: {client_ip}", client_ip)
    await db.commit()
    await db.refresh(order)

    # 构造返回，添加pay_url
    result = OrderResponse.model_validate(order).model_dump()
    if req.return_pay_url and order.pay_status == "pending_pay":
        result["pay_url"] = f"/pay/{order.order_no}"
    return result


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


# ============ 支付页面相关API（公开访问，不需要登录）============

@router.get("/pay/{order_no}")
async def get_payment_page(
    order_no: str,
    db: AsyncSession = Depends(get_db)
):
    """获取支付页面信息（公开访问）"""
    result = await db.execute(select(Order).where(Order.order_no == order_no))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查是否已过期
    now = datetime.now(timezone.utc)
    if order.pay_expire_at and now > order.pay_expire_at and order.pay_status == "pending_pay":
        order.pay_status = "expired"
        await db.commit()

    # 获取所有启用的收款账户（微信+支付宝）
    from app.models.payment_account import PaymentAccount
    accounts_result = await db.execute(
        select(PaymentAccount).where(PaymentAccount.status == "active").order_by(PaymentAccount.is_default.desc(), PaymentAccount.id)
    )
    accounts = accounts_result.scalars().all()

    payment_accounts = [
        {
            "id": a.id,
            "platform": a.platform,
            "account_name": a.account_name,
            "qr_code_url": a.qr_code_url,
        }
        for a in accounts
    ]

    return {
        "order_no": order.order_no,
        "total_amount": float(order.total_amount),
        "product_name": order.product_name,
        "payer_name": order.payer_name,
        "pay_status": order.pay_status,
        "pay_expire_at": order.pay_expire_at.isoformat() if order.pay_expire_at else None,
        "payment_accounts": payment_accounts,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


@router.post("/pay/{order_no}/confirm")
async def payer_confirm_payment(
    order_no: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """客户点击"我已支付"（公开访问）"""
    result = await db.execute(select(Order).where(Order.order_no == order_no))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.pay_status not in ["pending_pay", "pending_confirm"]:
        raise HTTPException(status_code=400, detail=f"当前订单状态为{order.pay_status}，无法确认支付")

    # 检查是否已过期
    now = datetime.now(timezone.utc)
    if order.pay_expire_at and now > order.pay_expire_at:
        order.pay_status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="支付链接已过期，请重新下单")

    client_ip = request.client.host if request.client else ""
    order.pay_status = "pending_confirm"
    order.payer_confirm_at = now
    order.pay_expire_at = None  # 客户确认后取消过期时间

    await log_operation(db, None, "payer_confirm_payment", "order", order.id,
                         f"客户确认已支付，IP: {client_ip}", client_ip)
    await db.commit()

    return {"success": True, "message": "已确认支付，等待商家确认收款", "pay_status": "pending_confirm"}


# ============ 管理员确认收款（需要登录）============

@router.post("/{order_id}/confirm-payment")
async def admin_confirm_payment(
    order_id: int,
    req: AdminConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """管理员确认收款（确认后自动分账）"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.pay_status not in ["pending_pay", "pending_confirm"]:
        raise HTTPException(status_code=400, detail=f"当前订单状态为{order.pay_status}，无法确认收款")

    now = datetime.now(timezone.utc)
    order.pay_status = "paid"
    order.paid_at = now
    order.pay_expire_at = None
    if req.transaction_id:
        order.transaction_id = req.transaction_id

    # 确认收款后自动分账
    if req.auto_share and order.share_status == "pending":
        rule = await ShareEngine.get_applicable_rule(db, order)
        if rule:
            await ShareEngine.execute_share(db, order, rule, current_user.id)
        else:
            order.share_status = "skipped"

    await log_operation(db, current_user, "admin_confirm_payment", "order", order.id,
                         f"管理员确认收款，订单金额 {order.total_amount}", "")
    await db.commit()
    await db.refresh(order)

    # 确认收款后，后台异步发送支付回调通知到业务系统
    # 从数据库读取配置（优先使用数据库配置，没有则用.env默认值）
    db_notify_url = await system_config_service.get_config(db, "payment_notify_url", settings.PAYMENT_NOTIFY_URL)
    db_app_id = await system_config_service.get_config(db, "payment_app_id", settings.PAYMENT_APP_ID)
    db_api_keys_str = await system_config_service.get_config(db, "api_keys", settings.API_KEYS)
    db_api_key = None
    if db_api_keys_str:
        db_api_key = str(db_api_keys_str).split(",")[0].strip()

    if db_notify_url:
        try:
            # 预提取订单数据，避免后台任务访问detached的SQLAlchemy对象
            order_data = {
                "order_no": str(order.order_no),
                "out_order_no": str(order.out_order_no or ""),
                "total_amount": f"{float(order.total_amount):.2f}",
                "paid_at": order.paid_at.strftime("%Y-%m-%d %H:%M:%S") if order.paid_at else "",
                "transaction_id": str(order.transaction_id or ""),
            }
            notify_service.send_payment_notify_background(
                order_data,
                notify_url=db_notify_url,
                api_key=db_api_key,
                app_id=str(db_app_id)
            )
            logger.info(f"订单 {order.order_no} 已触发支付回调通知 -> {db_notify_url}")
        except Exception as e:
            logger.error(f"订单 {order.order_no} 触发支付回调失败: {str(e)[:200]}")

    return {"success": True, "message": "确认收款成功", "order": OrderResponse.model_validate(order).model_dump()}
