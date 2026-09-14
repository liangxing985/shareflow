"""分账方余额模型"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ShareBalance(Base):
    __tablename__ = "share_balances"

    id = Column(Integer, primary_key=True, index=True)
    shareholder_id = Column(Integer, ForeignKey("shareholders.id"), unique=True, nullable=False, index=True, comment="分账方ID")
    shareholder_name = Column(String(100), nullable=False, comment="分账方名称（冗余）")

    # 累计统计
    total_receivable = Column(Numeric(14, 2), default=0, comment="累计应收金额")
    total_settled = Column(Numeric(14, 2), default=0, comment="累计已结算金额")
    total_adjusted = Column(Numeric(14, 2), default=0, comment="累计调整金额")

    # 当前余额
    current_balance = Column(Numeric(14, 2), default=0, comment="当前可结算余额")
    pending_balance = Column(Numeric(14, 2), default=0, comment="结算中余额（已生成结算单但未确认）")

    # 订单统计
    total_orders = Column(Integer, default=0, comment="累计分账订单数")
    settled_orders = Column(Integer, default=0, comment="已结算订单数")

    last_settlement_at = Column(DateTime(timezone=True), nullable=True, comment="最后结算时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
