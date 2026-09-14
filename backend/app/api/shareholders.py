"""分账方管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.database import get_db
from app.models.user import User
from app.models.shareholder import Shareholder
from app.models.share_balance import ShareBalance
from app.models.share_record import ShareRecord
from app.schemas.shareholder import ShareholderCreate, ShareholderUpdate, ShareholderResponse, ShareholderBalanceResponse
from app.schemas.common import PageResponse
from app.dependencies import get_current_user, require_manager

router = APIRouter(prefix="/shareholders", tags=["分账方管理"])


@router.get("", response_model=PageResponse[ShareholderResponse])
async def list_shareholders(
    page: int = 1, page_size: int = 20,
    keyword: str = None, shareholder_type: str = None, status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """分账方列表"""
    query = select(Shareholder)
    count_query = select(func.count(Shareholder.id))

    if keyword:
        condition = or_(Shareholder.name.contains(keyword), Shareholder.contact.contains(keyword),
                        Shareholder.wechat_account.contains(keyword), Shareholder.alipay_account.contains(keyword))
        query = query.where(condition)
        count_query = count_query.where(condition)
    if shareholder_type:
        query = query.where(Shareholder.shareholder_type == shareholder_type)
        count_query = count_query.where(Shareholder.shareholder_type == shareholder_type)
    if status:
        query = query.where(Shareholder.status == status)
        count_query = count_query.where(Shareholder.status == status)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Shareholder.id.desc()).offset((page - 1) * page_size).limit(page_size)
    shareholders = (await db.execute(query)).scalars().all()

    return PageResponse(items=shareholders, total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size)


@router.get("/with-balance", response_model=PageResponse[ShareholderBalanceResponse])
async def list_shareholders_with_balance(
    page: int = 1, page_size: int = 50,
    keyword: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """分账方列表（含余额）"""
    query = select(Shareholder)
    count_query = select(func.count(Shareholder.id))

    if keyword:
        condition = or_(Shareholder.name.contains(keyword), Shareholder.contact.contains(keyword))
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Shareholder.id.desc()).offset((page - 1) * page_size).limit(page_size)
    shareholders = (await db.execute(query)).scalars().all()

    # 批量查余额
    shareholder_ids = [s.id for s in shareholders]
    balances = {}
    if shareholder_ids:
        bal_result = await db.execute(select(ShareBalance).where(ShareBalance.shareholder_id.in_(shareholder_ids)))
        for bal in bal_result.scalars().all():
            balances[bal.shareholder_id] = bal

    result = []
    for sh in shareholders:
        sh_dict = ShareholderResponse.model_validate(sh).model_dump()
        bal = balances.get(sh.id)
        if bal:
            sh_dict.update({
                "total_receivable": float(bal.total_receivable),
                "total_settled": float(bal.total_settled),
                "current_balance": float(bal.current_balance),
                "pending_balance": float(bal.pending_balance),
                "total_orders": bal.total_orders,
            })
        else:
            sh_dict.update({
                "total_receivable": 0, "total_settled": 0,
                "current_balance": 0, "pending_balance": 0, "total_orders": 0,
            })
        result.append(sh_dict)

    return PageResponse(items=result, total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size)


@router.get("/{shareholder_id}", response_model=ShareholderBalanceResponse)
async def get_shareholder(
    shareholder_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """分账方详情（含余额）"""
    result = await db.execute(select(Shareholder).where(Shareholder.id == shareholder_id))
    shareholder = result.scalar_one_or_none()
    if not shareholder:
        raise HTTPException(status_code=404, detail="分账方不存在")

    bal_result = await db.execute(select(ShareBalance).where(ShareBalance.shareholder_id == shareholder_id))
    balance = bal_result.scalar_one_or_none()

    sh_dict = ShareholderResponse.model_validate(shareholder).model_dump()
    if balance:
        sh_dict.update({
            "total_receivable": float(balance.total_receivable),
            "total_settled": float(balance.total_settled),
            "current_balance": float(balance.current_balance),
            "pending_balance": float(balance.pending_balance),
            "total_orders": balance.total_orders,
        })
    return sh_dict


@router.post("", response_model=ShareholderResponse)
async def create_shareholder(
    req: ShareholderCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """创建分账方"""
    shareholder = Shareholder(**req.model_dump(), created_by=current_user.id)
    db.add(shareholder)
    await db.commit()
    await db.refresh(shareholder)

    # 初始化余额
    balance = ShareBalance(shareholder_id=shareholder.id, shareholder_name=shareholder.name)
    db.add(balance)
    await db.commit()

    return shareholder


@router.put("/{shareholder_id}", response_model=ShareholderResponse)
async def update_shareholder(
    shareholder_id: int, req: ShareholderUpdate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """更新分账方"""
    result = await db.execute(select(Shareholder).where(Shareholder.id == shareholder_id))
    shareholder = result.scalar_one_or_none()
    if not shareholder:
        raise HTTPException(status_code=404, detail="分账方不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(shareholder, key, value)

    await db.commit()
    await db.refresh(shareholder)
    return shareholder


@router.post("/{shareholder_id}/toggle-blacklist")
async def toggle_blacklist(
    shareholder_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """切换黑名单状态"""
    result = await db.execute(select(Shareholder).where(Shareholder.id == shareholder_id))
    shareholder = result.scalar_one_or_none()
    if not shareholder:
        raise HTTPException(status_code=404, detail="分账方不存在")

    shareholder.is_blacklisted = not shareholder.is_blacklisted
    await db.commit()
    return {"success": True, "is_blacklisted": shareholder.is_blacklisted}


@router.get("/{shareholder_id}/records")
async def get_shareholder_records(
    shareholder_id: int,
    page: int = 1, page_size: int = 20,
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """分账方的分账明细"""
    query = select(ShareRecord).where(ShareRecord.shareholder_id == shareholder_id)
    count_query = select(func.count(ShareRecord.id)).where(ShareRecord.shareholder_id == shareholder_id)

    if status:
        query = query.where(ShareRecord.status == status)
        count_query = count_query.where(ShareRecord.status == status)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(ShareRecord.id.desc()).offset((page - 1) * page_size).limit(page_size)
    records = (await db.execute(query)).scalars().all()

    return PageResponse(
        items=[{"id": r.id, "order_no": r.order_no, "share_amount": float(r.share_amount),
                "actual_amount": float(r.actual_amount) if r.actual_amount else None,
                "level": r.level, "status": r.status, "created_at": r.created_at.isoformat() if r.created_at else None}
               for r in records],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )
