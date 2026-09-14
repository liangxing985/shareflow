"""订单模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(64), unique=True, nullable=False, index=True, comment="订单号（业务系统传入或系统生成）")
    out_order_no = Column(String(64), nullable=True, index=True, comment="外部订单号（业务系统订单号）")

    # 金额
    total_amount = Column(Numeric(12, 2), nullable=False, comment="订单总金额（元）")
    platform_fee = Column(Numeric(12, 2), default=0, comment="平台抽成金额")
    shareable_amount = Column(Numeric(12, 2), default=0, comment="可分账金额（总金额-平台抽成）")

    # 收款信息
    payment_account_id = Column(Integer, ForeignKey("payment_accounts.id"), nullable=True, comment="收款账户ID")
    payer_name = Column(String(100), nullable=True, comment="付款人名称")
    payer_contact = Column(String(100), nullable=True, comment="付款人联系方式")

    # 商品/业务信息
    product_name = Column(String(200), nullable=True, comment="商品/业务名称")
    product_desc = Column(Text, nullable=True, comment="商品描述")
    category = Column(String(50), nullable=True, index=True, comment="业务分类")

    # 分账规则
    share_rule_id = Column(Integer, ForeignKey("share_rules.id"), nullable=True, comment="使用的分账规则ID")
    share_status = Column(String(20), default="pending", comment="分账状态: pending(待分账)/done(已分账)/skipped(跳过)")
    shared_at = Column(DateTime(timezone=True), nullable=True, comment="分账完成时间")

    # 支付信息
    pay_status = Column(String(20), default="pending_pay", comment="支付状态: pending_pay(待支付)/pending_confirm(待确认收款)/paid(已支付)/expired(已过期)/refunded(已退款)")
    paid_at = Column(DateTime(timezone=True), nullable=True, comment="支付时间")
    pay_expire_at = Column(DateTime(timezone=True), nullable=True, comment="支付链接过期时间")
    transaction_id = Column(String(100), nullable=True, comment="微信/支付宝交易号")
    payer_confirm_at = Column(DateTime(timezone=True), nullable=True, comment="客户点击已支付时间")

    # 来源
    source = Column(String(50), default="manual", comment="来源: manual(手动录入)/api(API接入)/import(批量导入)")
    api_app_id = Column(String(64), nullable=True, comment="API接入方标识")

    # 其他
    remark = Column(String(500), nullable=True, comment="备注")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_orders_paid_at', 'paid_at'),
        Index('idx_orders_category', 'category'),
    )
