"""对账记录模型"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class Reconciliation(Base):
    __tablename__ = "reconciliations"

    id = Column(Integer, primary_key=True, index=True)
    recon_no = Column(String(64), unique=True, nullable=False, index=True, comment="对账批次号")
    platform = Column(String(20), nullable=False, index=True, comment="平台: wechat/alipay/all")
    recon_date = Column(String(10), nullable=False, index=True, comment="对账日期 YYYY-MM-DD")

    # 统计
    system_orders = Column(Integer, default=0, comment="系统订单数")
    system_amount = Column(Numeric(14, 2), default=0, comment="系统订单金额")
    channel_orders = Column(Integer, default=0, comment="渠道订单数")
    channel_amount = Column(Numeric(14, 2), default=0, comment="渠道订单金额")

    matched_orders = Column(Integer, default=0, comment="匹配订单数")
    matched_amount = Column(Numeric(14, 2), default=0, comment="匹配金额")
    diff_orders = Column(Integer, default=0, comment="差异订单数")
    diff_amount = Column(Numeric(14, 2), default=0, comment="差异金额")

    # 差异明细
    diff_details = Column(JSON, nullable=True, comment="差异明细列表")

    # 状态
    status = Column(String(20), default="processing", comment="状态: processing(处理中)/completed(已完成)/has_diff(有差异)/failed(失败)")
    file_name = Column(String(200), nullable=True, comment="对账单文件名")
    file_url = Column(String(500), nullable=True, comment="对账单文件URL")

    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")
