"""分账方Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ShareholderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    contact: Optional[str] = None
    email: Optional[str] = None
    wechat_account: Optional[str] = None
    wechat_real_name: Optional[str] = None
    alipay_account: Optional[str] = None
    alipay_real_name: Optional[str] = None
    bank_name: Optional[str] = None
    bank_card_no: Optional[str] = None
    bank_account_name: Optional[str] = None
    preferred_payment: str = "wechat"
    default_rate: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    shareholder_type: str = "partner"
    remark: Optional[str] = None


class ShareholderUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    wechat_account: Optional[str] = None
    wechat_real_name: Optional[str] = None
    alipay_account: Optional[str] = None
    alipay_real_name: Optional[str] = None
    bank_name: Optional[str] = None
    bank_card_no: Optional[str] = None
    bank_account_name: Optional[str] = None
    preferred_payment: Optional[str] = None
    default_rate: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    shareholder_type: Optional[str] = None
    status: Optional[str] = None
    is_blacklisted: Optional[bool] = None
    remark: Optional[str] = None


class ShareholderResponse(BaseModel):
    id: int
    name: str
    contact: Optional[str] = None
    email: Optional[str] = None
    wechat_account: Optional[str] = None
    alipay_account: Optional[str] = None
    preferred_payment: str
    default_rate: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    shareholder_type: str
    status: str
    is_blacklisted: bool
    remark: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ShareholderBalanceResponse(ShareholderResponse):
    total_receivable: Optional[Decimal] = None
    total_settled: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None
    pending_balance: Optional[Decimal] = None
    total_orders: Optional[int] = None
