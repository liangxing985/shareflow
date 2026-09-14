"""收款账户路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User
from app.models.payment_account import PaymentAccount
from app.schemas.payment import PaymentAccountCreate, PaymentAccountUpdate, PaymentAccountResponse
from app.schemas.common import PageResponse
from app.dependencies import get_current_user, require_manager

router = APIRouter(prefix="/payment-accounts", tags=["收款账户"])


@router.get("", response_model=PageResponse[PaymentAccountResponse])
async def list_accounts(
    page: int = 1, page_size: int = 20,
    platform: str = None, status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """收款账户列表"""
    query = select(PaymentAccount)
    count_query = select(func.count(PaymentAccount.id))

    if platform:
        query = query.where(PaymentAccount.platform == platform)
        count_query = count_query.where(PaymentAccount.platform == platform)
    if status:
        query = query.where(PaymentAccount.status == status)
        count_query = count_query.where(PaymentAccount.status == status)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(PaymentAccount.is_default.desc(), PaymentAccount.id.desc()).offset((page - 1) * page_size).limit(page_size)
    accounts = (await db.execute(query)).scalars().all()

    return PageResponse(items=accounts, total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size)


@router.post("", response_model=PaymentAccountResponse)
async def create_account(
    req: PaymentAccountCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """创建收款账户"""
    if req.is_default:
        # 取消其他默认
        result = await db.execute(select(PaymentAccount).where(PaymentAccount.is_default == True, PaymentAccount.platform == req.platform))
        for acc in result.scalars().all():
            acc.is_default = False

    account = PaymentAccount(**req.model_dump(), created_by=current_user.id)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.put("/{account_id}", response_model=PaymentAccountResponse)
async def update_account(
    account_id: int, req: PaymentAccountUpdate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """更新收款账户"""
    result = await db.execute(select(PaymentAccount).where(PaymentAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="收款账户不存在")

    if req.is_default and not account.is_default:
        result2 = await db.execute(select(PaymentAccount).where(PaymentAccount.is_default == True, PaymentAccount.platform == account.platform))
        for acc in result2.scalars().all():
            acc.is_default = False

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)

    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """删除收款账户（禁用）"""
    result = await db.execute(select(PaymentAccount).where(PaymentAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="收款账户不存在")

    account.status = "disabled"
    await db.commit()
    return {"success": True}
