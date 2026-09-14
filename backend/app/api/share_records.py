"""分账明细路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from decimal import Decimal
from app.database import get_db
from app.models.user import User
from app.models.share_record import ShareRecord
from app.models.share_balance import ShareBalance
from app.schemas.common import PageResponse
from app.dependencies import get_current_user, require_finance
from app.services.share_service import to_decimal

router = APIRouter(prefix="/share-records", tags=["分账明细"])


@router.get("")
async def list_records(
    page: int = 1, page_size: int = 20,
    keyword: str = None, shareholder_id: int = None,
    status: str = None, level: int = None,
    start_date: str = None, end_date: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """分账明细列表"""
    query = select(ShareRecord)
    count_query = select(func.count(ShareRecord.id))

    if keyword:
        condition = or_(ShareRecord.order_no.contains(keyword), ShareRecord.shareholder_name.contains(keyword))
        query = query.where(condition)
        count_query = count_query.where(condition)
    if shareholder_id:
        query = query.where(ShareRecord.shareholder_id == shareholder_id)
        count_query = count_query.where(ShareRecord.shareholder_id == shareholder_id)
    if status:
        query = query.where(ShareRecord.status == status)
        count_query = count_query.where(ShareRecord.status == status)
    if level:
        query = query.where(ShareRecord.level == level)
        count_query = count_query.where(ShareRecord.level == level)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(ShareRecord.id.desc()).offset((page - 1) * page_size).limit(page_size)
    records = (await db.execute(query)).scalars().all()

    return PageResponse(
        items=[{"id": r.id, "order_id": r.order_id, "order_no": r.order_no,
                "shareholder_id": r.shareholder_id, "shareholder_name": r.shareholder_name,
                "order_amount": float(r.order_amount), "platform_fee": float(r.platform_fee) if r.platform_fee else 0,
                "shareable_amount": float(r.shareable_amount),
                "share_rate": float(r.share_rate) if r.share_rate else None,
                "share_amount": float(r.share_amount),
                "actual_amount": float(r.actual_amount) if r.actual_amount else None,
                "level": r.level, "parent_shareholder_id": r.parent_shareholder_id,
                "status": r.status, "settlement_id": r.settlement_id,
                "is_adjusted": r.is_adjusted, "adjust_reason": r.adjust_reason,
                "created_at": r.created_at.isoformat() if r.created_at else None}
               for r in records],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/{record_id}/adjust")
async def adjust_record(
    record_id: int,
    actual_amount: Decimal,
    reason: str,
    current_user: User = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
):
    """人工调整分账金额"""
    result = await db.execute(select(ShareRecord).where(ShareRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="分账明细不存在")
    if record.status in ["settled", "settling"]:
        raise HTTPException(status_code=400, detail="已结算或结算中的明细不能调整")

    old_amount = to_decimal(record.actual_amount or record.share_amount)
    diff = actual_amount - old_amount

    record.actual_amount = actual_amount
    record.is_adjusted = 1
    record.adjust_reason = reason

    # 更新余额
    bal_result = await db.execute(select(ShareBalance).where(ShareBalance.shareholder_id == record.shareholder_id))
    balance = bal_result.scalar_one_or_none()
    if balance:
        balance.total_receivable = to_decimal(balance.total_receivable) + diff
        balance.current_balance = to_decimal(balance.current_balance) + diff
        balance.total_adjusted = to_decimal(balance.total_adjusted) + diff

    await db.commit()
    return {"success": True, "message": "调整完成", "old_amount": float(old_amount), "new_amount": float(actual_amount)}


@router.get("/stats/summary")
async def records_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """分账明细统计"""
    total_records = (await db.execute(select(func.count(ShareRecord.id)))).scalar()
    total_amount = (await db.execute(select(func.coalesce(func.sum(ShareRecord.share_amount), 0)))).scalar()
    pending_amount = (await db.execute(select(func.coalesce(func.sum(ShareRecord.share_amount), 0)).where(ShareRecord.status == "pending"))).scalar()
    settled_amount = (await db.execute(select(func.coalesce(func.sum(ShareRecord.actual_amount), 0)).where(ShareRecord.status == "settled"))).scalar()

    return {
        "total_records": total_records,
        "total_amount": float(total_amount),
        "pending_amount": float(pending_amount),
        "settled_amount": float(settled_amount),
    }
