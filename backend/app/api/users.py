"""用户管理路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserUpdate, UserResponse
from app.schemas.common import PageResponse
from app.core.security import hash_password
from app.dependencies import require_admin, get_current_user

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", response_model=PageResponse[UserResponse])
async def list_users(
    page: int = 1, page_size: int = 20,
    keyword: str = None, role: str = None, status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """用户列表"""
    query = select(User)
    count_query = select(func.count(User.id))

    if keyword:
        query = query.where(or_(User.username.contains(keyword), User.full_name.contains(keyword), User.email.contains(keyword)))
        count_query = count_query.where(or_(User.username.contains(keyword), User.full_name.contains(keyword), User.email.contains(keyword)))
    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
        count_query = count_query.where(User.status == status)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(query)).scalars().all()

    return PageResponse(items=users, total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size)


@router.post("", response_model=UserResponse)
async def create_user(
    req: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """创建用户"""
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=req.username,
        hashed_password=hash_password(req.password),
        email=req.email,
        phone=req.phone,
        full_name=req.full_name,
        role=req.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, req: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    update_data = req.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
    elif "password" in update_data:
        update_data.pop("password")

    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除用户（禁用）"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.status = "disabled"
    await db.commit()
    return {"success": True, "message": "用户已禁用"}
