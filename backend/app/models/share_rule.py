"""分账规则模型"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, Boolean, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ShareRule(Base):
    __tablename__ = "share_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="规则名称")
    description = Column(String(500), nullable=True, comment="规则描述")

    # 适用范围
    scope_type = Column(String(20), default="global", comment="适用范围: global(全局)/category(按分类)/specific(指定订单)")
    scope_value = Column(String(200), nullable=True, comment="范围值（分类名等）")

    # 平台抽成
    platform_fee_rate = Column(Numeric(5, 4), default=0.10, comment="平台抽成比例（0-1）")
    platform_fee_fixed = Column(Numeric(12, 2), nullable=True, comment="平台固定抽成金额（与比例二选一）")

    # 分账明细（JSON数组，支持多级分账）
    # 格式: [{"shareholder_id": 1, "rate": 0.6, "level": 1, "parent_id": null}, ...]
    share_details = Column(JSON, nullable=False, comment="分账明细配置")

    # 多级分账配置
    enable_multi_level = Column(Boolean, default=False, comment="是否启用多级分账")
    max_levels = Column(Integer, default=2, comment="最大分账层级")

    # 规则状态
    is_default = Column(Boolean, default=False, comment="是否默认规则")
    status = Column(String(20), default="active", comment="状态: active/inactive")
    priority = Column(Integer, default=0, comment="优先级（数字越大越优先）")

    effective_from = Column(DateTime(timezone=True), nullable=True, comment="生效开始时间")
    effective_to = Column(DateTime(timezone=True), nullable=True, comment="生效结束时间")

    remark = Column(String(500), nullable=True, comment="备注")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
