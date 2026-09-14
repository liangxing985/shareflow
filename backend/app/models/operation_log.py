"""操作日志模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True, comment="操作人ID")
    username = Column(String(50), nullable=True, comment="操作人用户名（冗余）")

    module = Column(String(50), nullable=False, index=True, comment="模块: auth/order/shareholder/rule/settlement/reconciliation/system")
    action = Column(String(50), nullable=False, comment="操作: create/update/delete/export/import/login/confirm/cancel")
    target_type = Column(String(50), nullable=True, comment="操作对象类型")
    target_id = Column(Integer, nullable=True, comment="操作对象ID")

    description = Column(String(500), nullable=True, comment="操作描述")
    before_data = Column(JSON, nullable=True, comment="操作前数据")
    after_data = Column(JSON, nullable=True, comment="操作后数据")

    ip_address = Column(String(50), nullable=True, comment="IP地址")
    user_agent = Column(String(500), nullable=True, comment="User-Agent")
    status = Column(String(20), default="success", comment="状态: success/failed")
    error_msg = Column(String(500), nullable=True, comment="错误信息")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
