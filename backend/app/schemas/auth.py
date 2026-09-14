"""认证Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    status: str
    avatar: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "operator"


class UserUpdate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None
