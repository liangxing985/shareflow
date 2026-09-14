"""订单Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class OrderCreate(BaseModel):
    """手动创建订单"""
    order_no: Optional[str] = None
    out_order_no: Optional[str] = None
    total_amount: Decimal = Field(..., gt=0)
    payment_account_id: Optional[int] = None
    payer_name: Optional[str] = None
    payer_contact: Optional[str] = None
    product_name: Optional[str] = None
    product_desc: Optional[str] = None
    category: Optional[str] = None
    share_rule_id: Optional[int] = None
    paid_at: Optional[datetime] = None
    transaction_id: Optional[str] = None
    remark: Optional[str] = None
    auto_share: bool = True


class OrderApiCreate(BaseModel):
    """API接入创建订单（业务系统对接）"""
    out_order_no: str = Field(..., min_length=1, max_length=64)
    total_amount: Decimal = Field(..., gt=0)
    product_name: Optional[str] = None
    product_desc: Optional[str] = None
    category: Optional[str] = None
    payer_name: Optional[str] = None
    payer_contact: Optional[str] = None
    share_rule_id: Optional[int] = None
    remark: Optional[str] = None
    auto_share: bool = True


class OrderUpdate(BaseModel):
    payment_account_id: Optional[int] = None
    payer_name: Optional[str] = None
    payer_contact: Optional[str] = None
    product_name: Optional[str] = None
    product_desc: Optional[str] = None
    category: Optional[str] = None
    share_rule_id: Optional[int] = None
    pay_status: Optional[str] = None
    transaction_id: Optional[str] = None
    remark: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    order_no: str
    out_order_no: Optional[str] = None
    total_amount: Decimal
    platform_fee: Optional[Decimal] = None
    shareable_amount: Optional[Decimal] = None
    payment_account_id: Optional[int] = None
    payer_name: Optional[str] = None
    product_name: Optional[str] = None
    category: Optional[str] = None
    share_rule_id: Optional[int] = None
    share_status: str
    pay_status: str
    paid_at: Optional[datetime] = None
    transaction_id: Optional[str] = None
    source: str
    remark: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderDetailResponse(OrderResponse):
    share_records: Optional[List[dict]] = None


class OrderListRequest(BaseModel):
    page: int = 1
    page_size: int = 20
    keyword: Optional[str] = None
    category: Optional[str] = None
    share_status: Optional[str] = None
    pay_status: Optional[str] = None
    source: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
