"""分账规则Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class ShareDetailItem(BaseModel):
    """分账明细项"""
    shareholder_id: int
    rate: Decimal = Field(..., ge=0, le=1)
    level: int = 1
    parent_id: Optional[int] = None


class ShareRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    scope_type: str = "global"
    scope_value: Optional[str] = None
    platform_fee_rate: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    platform_fee_fixed: Optional[Decimal] = None
    share_details: List[ShareDetailItem] = Field(..., min_length=1)
    enable_multi_level: bool = False
    max_levels: int = 2
    is_default: bool = False
    priority: int = 0
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    remark: Optional[str] = None


class ShareRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope_type: Optional[str] = None
    scope_value: Optional[str] = None
    platform_fee_rate: Optional[Decimal] = None
    platform_fee_fixed: Optional[Decimal] = None
    share_details: Optional[List[ShareDetailItem]] = None
    enable_multi_level: Optional[bool] = None
    max_levels: Optional[int] = None
    is_default: Optional[bool] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    remark: Optional[str] = None


class ShareRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    scope_type: str
    scope_value: Optional[str] = None
    platform_fee_rate: Decimal
    platform_fee_fixed: Optional[Decimal] = None
    share_details: List[dict]
    enable_multi_level: bool
    max_levels: int
    is_default: bool
    status: str
    priority: int
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
