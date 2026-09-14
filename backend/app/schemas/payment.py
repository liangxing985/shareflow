"""收款账户Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PaymentAccountCreate(BaseModel):
    platform: str = Field(..., pattern="^(wechat|alipay|bank)$")
    account_name: str = Field(..., min_length=1, max_length=100)
    account_no: Optional[str] = None
    qr_code_url: Optional[str] = None
    bank_name: Optional[str] = None
    bank_card_no: Optional[str] = None
    is_default: bool = False
    remark: Optional[str] = None


class PaymentAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    account_no: Optional[str] = None
    qr_code_url: Optional[str] = None
    bank_name: Optional[str] = None
    bank_card_no: Optional[str] = None
    is_default: Optional[bool] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class PaymentAccountResponse(BaseModel):
    id: int
    platform: str
    account_name: str
    account_no: Optional[str] = None
    qr_code_url: Optional[str] = None
    bank_name: Optional[str] = None
    bank_card_no: Optional[str] = None
    is_default: bool
    status: str
    remark: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
