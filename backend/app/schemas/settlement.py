"""结算Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class SettlementCreate(BaseModel):
    """创建结算单（生成转账清单）"""
    shareholder_id: int
    payment_method: str = "wechat"
    record_ids: Optional[List[int]] = None  # 指定分账明细，为空则结算所有待结算
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    remark: Optional[str] = None


class SettlementBatchCreate(BaseModel):
    """批量创建结算单（给多个分账方生成转账清单）"""
    shareholder_ids: Optional[List[int]] = None  # 为空则给所有有余额的分账方创建
    payment_method: str = "wechat"
    remark: Optional[str] = None


class SettlementTransfer(BaseModel):
    """登记转账"""
    transaction_no: Optional[str] = None
    transfer_voucher_url: Optional[str] = None
    actual_amount: Optional[Decimal] = None
    fee_amount: Optional[Decimal] = None
    remark: Optional[str] = None


class SettlementConfirm(BaseModel):
    """确认结算"""
    remark: Optional[str] = None


class SettlementResponse(BaseModel):
    id: int
    settlement_no: str
    shareholder_id: int
    shareholder_name: str
    total_records: int
    total_amount: Decimal
    actual_amount: Optional[Decimal] = None
    fee_amount: Optional[Decimal] = None
    payment_method: str
    transaction_no: Optional[str] = None
    transfer_voucher_url: Optional[str] = None
    status: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    transferred_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SettlementDetailResponse(SettlementResponse):
    share_records: Optional[List[dict]] = None


class TransferListItem(BaseModel):
    """转账清单项（导出用）"""
    shareholder_name: str
    payment_method: str
    account: str
    real_name: str
    amount: Decimal
    settlement_no: str
    remark: Optional[str] = None
