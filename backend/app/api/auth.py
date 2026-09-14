"""认证路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest, UserResponse
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    access_token = create_access_token({"user_id": user.id, "username": user.username, "role": user.role})
    refresh_token = create_refresh_token({"user_id": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/register", response_model=UserResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册（首个用户自动成为admin）"""
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查是否是第一个用户
    count_result = await db.execute(select(User))
    is_first = len(count_result.scalars().all()) == 0

    user = User(
        username=req.username,
        hashed_password=hash_password(req.password),
        email=req.email,
        full_name=req.full_name,
        phone=req.phone,
        role="admin" if is_first else "operator",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """刷新令牌"""
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的刷新令牌")

    user_id = payload.get("user_id")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    access_token = create_access_token({"user_id": user.id, "username": user.username, "role": user.role})
    new_refresh_token = create_refresh_token({"user_id": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user
