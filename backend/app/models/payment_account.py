"""收款账户模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.database import Base


class PaymentAccount(Base):
    __tablename__ = "payment_accounts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(20), nullable=False, index=True, comment="平台: wechat/alipay")
    account_name = Column(String(100), nullable=False, comment="账户名称（如：微信-张三）")
    account_no = Column(String(100), nullable=True, comment="账号（微信号/支付宝账号）")
    qr_code_url = Column(String(500), nullable=True, comment="收款码图片URL")
    bank_name = Column(String(100), nullable=True, comment="银行名称（银行卡时）")
    bank_card_no = Column(String(50), nullable=True, comment="银行卡号")
    is_default = Column(Boolean, default=False, comment="是否默认收款账户")
    status = Column(String(20), default="active", comment="状态: active/disabled")
    remark = Column(String(500), nullable=True, comment="备注")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
