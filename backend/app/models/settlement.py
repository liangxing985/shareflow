"""结算单模型"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(Integer, primary_key=True, index=True)
    settlement_no = Column(String(64), unique=True, nullable=False, index=True, comment="结算单号")

    shareholder_id = Column(Integer, ForeignKey("shareholders.id"), nullable=False, index=True, comment="分账方ID")
    shareholder_name = Column(String(100), nullable=False, comment="分账方名称（冗余）")

    # 金额
    total_records = Column(Integer, default=0, comment="包含分账明细数")
    total_amount = Column(Numeric(14, 2), nullable=False, comment="结算总金额")
    actual_amount = Column(Numeric(14, 2), nullable=True, comment="实际转账金额")
    fee_amount = Column(Numeric(12, 2), default=0, comment="手续费")

    # 结算方式
    payment_method = Column(String(20), default="wechat", comment="结算方式: wechat/alipay/bank/cash")
    transaction_no = Column(String(100), nullable=True, comment="转账交易号")
    transfer_voucher_url = Column(String(500), nullable=True, comment="转账凭证图片URL")

    # 状态流转
    status = Column(String(20), default="pending", comment="状态: pending(待转账)/transferred(已转账待确认)/confirmed(已确认)/failed(失败)/cancelled(已取消)")
    period_start = Column(DateTime(timezone=True), nullable=True, comment="结算周期开始")
    period_end = Column(DateTime(timezone=True), nullable=True, comment="结算周期结束")

    # 操作人
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    transferred_by = Column(Integer, nullable=True, comment="转账操作人ID")
    transferred_at = Column(DateTime(timezone=True), nullable=True, comment="转账时间")
    confirmed_by = Column(Integer, nullable=True, comment="确认人ID")
    confirmed_at = Column(DateTime(timezone=True), nullable=True, comment="确认时间")

    remark = Column(String(500), nullable=True, comment="备注")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_settlements_status', 'status'),
        Index('idx_settlements_shareholder', 'shareholder_id'),
    )
