"""分账明细模型"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class ShareRecord(Base):
    __tablename__ = "share_records"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True, comment="订单ID")
    order_no = Column(String(64), nullable=False, index=True, comment="订单号（冗余）")

    shareholder_id = Column(Integer, ForeignKey("shareholders.id"), nullable=False, index=True, comment="分账方ID")
    shareholder_name = Column(String(100), nullable=False, comment="分账方名称（冗余）")

    # 金额
    order_amount = Column(Numeric(12, 2), nullable=False, comment="订单总金额")
    platform_fee = Column(Numeric(12, 2), default=0, comment="平台抽成")
    shareable_amount = Column(Numeric(12, 2), nullable=False, comment="可分账金额")
    share_rate = Column(Numeric(5, 4), nullable=True, comment="分账比例")
    share_amount = Column(Numeric(12, 2), nullable=False, comment="应分账金额")
    actual_amount = Column(Numeric(12, 2), nullable=True, comment="实际分账金额（调整后）")

    # 多级分账
    level = Column(Integer, default=1, comment="分账层级（1=一级，2=二级...）")
    parent_shareholder_id = Column(Integer, nullable=True, comment="上级分账方ID")
    parent_amount = Column(Numeric(12, 2), nullable=True, comment="上级分账金额（二级分账基于此计算）")

    # 状态
    status = Column(String(20), default="pending", comment="状态: pending(待结算)/settling(结算中)/settled(已结算)/failed(失败)")
    settlement_id = Column(Integer, ForeignKey("settlements.id"), nullable=True, comment="结算单ID")
    settled_at = Column(DateTime(timezone=True), nullable=True, comment="结算时间")

    # 调整
    is_adjusted = Column(Integer, default=0, comment="是否人工调整: 0否/1是")
    adjust_reason = Column(String(500), nullable=True, comment="调整原因")

    remark = Column(String(500), nullable=True, comment="备注")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_share_records_shareholder_status', 'shareholder_id', 'status'),
    )
