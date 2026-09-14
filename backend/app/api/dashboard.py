"""数据看板路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from app.database import get_db
from app.models.user import User
from app.models.order import Order
from app.models.share_record import ShareRecord
from app.models.share_balance import ShareBalance
from app.models.settlement import Settlement
from app.models.shareholder import Shareholder
from app.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["数据看板"])


@router.get("/overview")
async def dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """看板概览数据"""
    # 订单统计
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar()
    total_amount = (await db.execute(select(func.coalesce(func.sum(Order.total_amount), 0)))).scalar()
    total_platform_fee = (await db.execute(select(func.coalesce(func.sum(Order.platform_fee), 0)))).scalar()

    # 今日
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = (await db.execute(select(func.count(Order.id)).where(Order.created_at >= today_start))).scalar()
    today_amount = (await db.execute(select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.created_at >= today_start))).scalar()

    # 分账统计
    total_share_amount = (await db.execute(select(func.coalesce(func.sum(ShareRecord.share_amount), 0)))).scalar()
    pending_share_amount = (await db.execute(select(func.coalesce(func.sum(ShareRecord.share_amount), 0)).where(ShareRecord.status == "pending"))).scalar()

    # 结算统计
    total_settled_amount = (await db.execute(select(func.coalesce(func.sum(Settlement.actual_amount), 0)).where(Settlement.status == "confirmed"))).scalar()
    pending_settlement_count = (await db.execute(select(func.count(Settlement.id)).where(Settlement.status.in_(["pending", "transferred"])))).scalar()

    # 分账方和待结算余额
    shareholder_count = (await db.execute(select(func.count(Shareholder.id)).where(Shareholder.status == "active"))).scalar()
    total_pending_balance = (await db.execute(select(func.coalesce(func.sum(ShareBalance.current_balance), 0)))).scalar()

    return {
        "orders": {
            "total": total_orders,
            "total_amount": float(total_amount),
            "today": today_orders,
            "today_amount": float(today_amount),
            "platform_fee": float(total_platform_fee),
        },
        "shares": {
            "total_amount": float(total_share_amount),
            "pending_amount": float(pending_share_amount),
            "shareholder_count": shareholder_count,
        },
        "settlements": {
            "total_settled": float(total_settled_amount),
            "pending_count": pending_settlement_count,
            "total_pending_balance": float(total_pending_balance),
        },
    }


@router.get("/trend")
async def dashboard_trend(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """趋势数据（近N天）"""
    end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start_date = end_date - timedelta(days=days)

    # 按天统计订单
    from sqlalchemy import func as sql_func
    date_col = sql_func.date(Order.created_at)

    result = await db.execute(
        select(date_col, func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0))
        .where(Order.created_at >= start_date, Order.created_at < end_date)
        .group_by(date_col)
        .order_by(date_col)
    )

    daily_data = {str(row[0]): {"orders": row[1], "amount": float(row[2])} for row in result.all()}

    # 补全日期
    dates = []
    orders = []
    amounts = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        dates.append(d)
        day_data = daily_data.get(d, {"orders": 0, "amount": 0})
        orders.append(day_data["orders"])
        amounts.append(day_data["amount"])

    # 分账趋势
    share_date_col = sql_func.date(ShareRecord.created_at)
    share_result = await db.execute(
        select(share_date_col, func.coalesce(func.sum(ShareRecord.share_amount), 0))
        .where(ShareRecord.created_at >= start_date, ShareRecord.created_at < end_date)
        .group_by(share_date_col)
    )
    share_daily = {str(row[0]): float(row[1]) for row in share_result.all()}
    share_amounts = [share_daily.get(d, 0) for d in dates]

    return {
        "dates": dates,
        "orders": orders,
        "order_amounts": amounts,
        "share_amounts": share_amounts,
    }


@router.get("/shareholder-ranking")
async def shareholder_ranking(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """分账方收益排行"""
    result = await db.execute(
        select(ShareBalance.shareholder_name, ShareBalance.total_receivable, ShareBalance.total_settled,
               ShareBalance.current_balance, ShareBalance.total_orders)
        .order_by(ShareBalance.total_receivable.desc())
        .limit(limit)
    )

    ranking = []
    for row in result.all():
        ranking.append({
            "name": row[0],
            "total_receivable": float(row[1] or 0),
            "total_settled": float(row[2] or 0),
            "current_balance": float(row[3] or 0),
            "total_orders": row[4] or 0,
        })

    return {"ranking": ranking}


@router.get("/platform-fee-trend")
async def platform_fee_trend(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """平台抽成趋势"""
    end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start_date = end_date - timedelta(days=days)

    from sqlalchemy import func as sql_func
    date_col = sql_func.date(Order.created_at)

    result = await db.execute(
        select(date_col, func.coalesce(func.sum(Order.platform_fee), 0), func.coalesce(func.sum(Order.total_amount), 0))
        .where(Order.created_at >= start_date, Order.created_at < end_date, Order.platform_fee > 0)
        .group_by(date_col)
        .order_by(date_col)
    )

    daily = {str(row[0]): {"fee": float(row[1]), "amount": float(row[2])} for row in result.all()}

    dates = []
    fees = []
    amounts = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        dates.append(d)
        day_data = daily.get(d, {"fee": 0, "amount": 0})
        fees.append(day_data["fee"])
        amounts.append(day_data["amount"])

    total_fee = sum(fees)
    total_amount = sum(amounts)
    avg_rate = (total_fee / total_amount * 100) if total_amount > 0 else 0

    return {
        "dates": dates,
        "fees": fees,
        "amounts": amounts,
        "total_fee": total_fee,
        "total_amount": total_amount,
        "avg_rate": round(avg_rate, 2),
    }
