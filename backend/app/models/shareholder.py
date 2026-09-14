"""分账方模型"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Shareholder(Base):
    __tablename__ = "shareholders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="分账方姓名/名称")
    contact = Column(String(100), nullable=True, comment="联系方式（手机/微信）")
    email = Column(String(100), nullable=True, comment="邮箱")

    # 收款方式
    wechat_account = Column(String(100), nullable=True, comment="微信账号")
    wechat_real_name = Column(String(50), nullable=True, comment="微信实名")
    alipay_account = Column(String(100), nullable=True, comment="支付宝账号")
    alipay_real_name = Column(String(50), nullable=True, comment="支付宝实名")
    bank_name = Column(String(100), nullable=True, comment="开户银行")
    bank_card_no = Column(String(50), nullable=True, comment="银行卡号")
    bank_account_name = Column(String(50), nullable=True, comment="银行开户名")
    preferred_payment = Column(String(20), default="wechat", comment="首选结算方式: wechat/alipay/bank")

    # 分账信息
    default_rate = Column(Numeric(5, 4), nullable=True, comment="默认分账比例（0-1）")
    fixed_amount = Column(Numeric(12, 2), nullable=True, comment="固定分账金额（元），与比例二选一")
    shareholder_type = Column(String(20), default="partner", comment="类型: partner(合伙人)/supplier(供应商)/promoter(推广员)/employee(员工)/other")

    # 状态
    status = Column(String(20), default="active", comment="状态: active/inactive")
    is_blacklisted = Column(Boolean, default=False, comment="是否黑名单（暂停分账）")

    remark = Column(String(500), nullable=True, comment="备注")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
