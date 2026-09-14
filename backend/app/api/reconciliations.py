"""对账管理路由"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
import uuid
from app.database import get_db
from app.models.user import User
from app.models.order import Order
from app.models.reconciliation import Reconciliation
from app.schemas.common import PageResponse
from app.dependencies import get_current_user, require_finance

router = APIRouter(prefix="/reconciliations", tags=["对账管理"])


def generate_recon_no() -> str:
    return f"RC{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


@router.get("", response_model=PageResponse[dict])
async def list_reconciliations(
    page: int = 1, page_size: int = 20,
    platform: str = None, status: str = None, recon_date: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """对账记录列表"""
    query = select(Reconciliation)
    count_query = select(func.count(Reconciliation.id))

    if platform:
        query = query.where(Reconciliation.platform == platform)
        count_query = count_query.where(Reconciliation.platform == platform)
    if status:
        query = query.where(Reconciliation.status == status)
        count_query = count_query.where(Reconciliation.status == status)
    if recon_date:
        query = query.where(Reconciliation.recon_date == recon_date)
        count_query = count_query.where(Reconciliation.recon_date == recon_date)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Reconciliation.id.desc()).offset((page - 1) * page_size).limit(page_size)
    records = (await db.execute(query)).scalars().all()

    return PageResponse(
        items=[{"id": r.id, "recon_no": r.recon_no, "platform": r.platform, "recon_date": r.recon_date,
                "system_orders": r.system_orders, "system_amount": float(r.system_amount),
                "channel_orders": r.channel_orders, "channel_amount": float(r.channel_amount),
                "matched_orders": r.matched_orders, "diff_orders": r.diff_orders,
                "diff_amount": float(r.diff_amount), "status": r.status,
                "file_name": r.file_name, "created_at": r.created_at.isoformat() if r.created_at else None}
               for r in records],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/upload")
async def upload_statement(
    platform: str,
    recon_date: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
):
    """上传微信/支付宝对账单（CSV/Excel），自动对账"""
    if platform not in ["wechat", "alipay"]:
        raise HTTPException(status_code=400, detail="平台只能是 wechat 或 alipay")

    # 读取文件内容
    content = await file.read()

    # 创建对账记录
    recon = Reconciliation(
        recon_no=generate_recon_no(),
        platform=platform,
        recon_date=recon_date,
        file_name=file.filename,
        status="processing",
        created_by=current_user.id,
    )
    db.add(recon)
    await db.flush()

    # 解析对账单（简化版：实际需要根据微信/支付宝对账单格式解析）
    # 这里先统计系统订单，标记为需要人工核对
    from datetime import datetime as dt
    date_start = dt.strptime(recon_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    date_end = date_start.replace(hour=23, minute=59, second=59)

    system_orders_result = await db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0))
        .where(Order.created_at >= date_start, Order.created_at <= date_end)
    )
    sys_count, sys_amount = system_orders_result.first()

    recon.system_orders = sys_count or 0
    recon.system_amount = sys_amount or 0
    recon.channel_orders = 0  # 需要解析文件后填充
    recon.channel_amount = 0
    recon.matched_orders = 0
    recon.diff_orders = sys_count or 0
    recon.diff_amount = sys_amount or 0
    recon.status = "has_diff"
    recon.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(recon)

    return {
        "success": True,
        "recon_id": recon.id,
        "recon_no": recon.recon_no,
        "message": "对账单已上传，系统订单已统计。请人工核对差异明细（微信/支付宝对账单格式需定制解析）",
        "system_orders": recon.system_orders,
        "system_amount": float(recon.system_amount),
    }


@router.get("/{recon_id}")
async def get_reconciliation(
    recon_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """对账详情"""
    result = await db.execute(select(Reconciliation).where(Reconciliation.id == recon_id))
    recon = result.scalar_one_or_none()
    if not recon:
        raise HTTPException(status_code=404, detail="对账记录不存在")

    return {
        "id": recon.id,
        "recon_no": recon.recon_no,
        "platform": recon.platform,
        "recon_date": recon.recon_date,
        "system_orders": recon.system_orders,
        "system_amount": float(recon.system_amount),
        "channel_orders": recon.channel_orders,
        "channel_amount": float(recon.channel_amount),
        "matched_orders": recon.matched_orders,
        "matched_amount": float(recon.matched_amount) if recon.matched_amount else 0,
        "diff_orders": recon.diff_orders,
        "diff_amount": float(recon.diff_amount),
        "diff_details": recon.diff_details,
        "status": recon.status,
        "file_name": recon.file_name,
        "created_at": recon.created_at.isoformat() if recon.created_at else None,
        "completed_at": recon.completed_at.isoformat() if recon.completed_at else None,
    }
