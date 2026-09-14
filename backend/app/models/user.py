"""用户模型"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=True, comment="邮箱")
    phone = Column(String(20), nullable=True, comment="手机号")
    full_name = Column(String(50), nullable=True, comment="真实姓名")
    hashed_password = Column(String(255), nullable=False, comment="密码哈希")
    role = Column(String(20), default="operator", comment="角色: admin/manager/operator/finance/viewer")
    status = Column(String(20), default="active", comment="状态: active/disabled")
    avatar = Column(String(500), nullable=True, comment="头像")
    last_login_at = Column(DateTime(timezone=True), nullable=True, comment="最后登录时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
