"""结算管理路由（核心：生成转账清单、登记转账、确认结算、导出）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid
from io import BytesIO
from fastapi.responses import StreamingResponse
from app.database import get_db
from app.models.user import User
from app.models.shareholder import Shareholder
from app.models.share_record import ShareRecord
from app.models.share_balance import ShareBalance
from app.models.settlement import Settlement
from app.schemas.settlement import SettlementCreate, SettlementBatchCreate, SettlementTransfer, SettlementConfirm, SettlementResponse, SettlementDetailResponse
from app.schemas.common import PageResponse
from app.dependencies import get_current_user, require_finance
from app.services.share_service import to_decimal

router = APIRouter(prefix="/settlements", tags=["结算管理"])


def generate_settlement_no() -> str:
    return f"ST{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


@router.get("", response_model=PageResponse[SettlementResponse])
async def list_settlements(
    page: int = 1, page_size: int = 20,
    keyword: str = None, shareholder_id: int = None,
    status: str = None, payment_method: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """结算单列表"""
    query = select(Settlement)
    count_query = select(func.count(Settlement.id))

    if keyword:
        from sqlalchemy import or_
        condition = or_(Settlement.settlement_no.contains(keyword), Settlement.shareholder_name.contains(keyword))
        query = query.where(condition)
        count_query = count_query.where(condition)
    if shareholder_id:
        query = query.where(Settlement.shareholder_id == shareholder_id)
        count_query = count_query.where(Settlement.shareholder_id == shareholder_id)
    if status:
        query = query.where(Settlement.status == status)
        count_query = count_query.where(Settlement.status == status)
    if payment_method:
        query = query.where(Settlement.payment_method == payment_method)
        count_query = count_query.where(Settlement.payment_method == payment_method)

    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Settlement.id.desc()).offset((page - 1) * page_size).limit(page_size)
    settlements = (await db.execute(query)).scalars().all()

    return PageResponse(items=settlements, total=total, page=page, page_size=page_size, total_pages=(total + page_size - 1) // page_size)


@router.get("/{settlement_id}", response_model=SettlementDetailResponse)
async def get_settlement(
    settlement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """结算单详情（含分账明细）"""
    result = await db.execute(select(Settlement).where(Settlement.id == settlement_id))
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(status_code=404, detail="结算单不存在")

    records_result = await db.execute(select(ShareRecord).where(ShareRecord.settlement_id == settlement_id).order_by(ShareRecord.id))
    records = records_result.scalars().all()

    set_dict = SettlementResponse.model_validate(settlement).model_dump()
    set_dict["share_records"] = [
        {"id": r.id, "order_no": r.order_no, "share_amount": float(r.share_amount),
         "actual_amount": float(r.actual_amount) if r.actual_amount else None, "level": r.level}
        for r in records
    ]
    return set_dict


@router.post("", response_model=SettlementResponse)
async def create_settlement(
    req: SettlementCreate,
    current_user: User = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
):
    """创建结算单（生成转账清单）"""
    # 查分账方
    sh_result = await db.execute(select(Shareholder).where(Shareholder.id == req.shareholder_id))
    shareholder = sh_result.scalar_one_or_none()
    if not shareholder:
        raise HTTPException(status_code=404, detail="分账方不存在")

    # 查待结算的分账明细
    query = select(ShareRecord).where(
        ShareRecord.shareholder_id == req.shareholder_id,
        ShareRecord.status == "pending"
    )
    if req.record_ids:
        query = query.where(ShareRecord.id.in_(req.record_ids))
    if req.period_start:
        query = query.where(ShareRecord.created_at >= req.period_start)
    if req.period_end:
        query = query.where(ShareRecord.created_at <= req.period_end)

    records = (await db.execute(query)).scalars().all()
    if not records:
        raise HTTPException(status_code=400, detail="没有待结算的分账明细")

    total_amount = sum(to_decimal(r.actual_amount or r.share_amount) for r in records)

    # 创建结算单
    settlement = Settlement(
        settlement_no=generate_settlement_no(),
        shareholder_id=shareholder.id,
        shareholder_name=shareholder.name,
        total_records=len(records),
        total_amount=total_amount,
        payment_method=req.payment_method,
        status="pending",
        period_start=req.period_start,
        period_end=req.period_end,
        remark=req.remark,
        created_by=current_user.id,
    )
    db.add(settlement)
    await db.flush()

    # 关联分账明细，更新状态和余额
    for record in records:
        record.settlement_id = settlement.id
        record.status = "settling"

    # 更新余额：从current_balance转到pending_balance
    bal_result = await db.execute(select(ShareBalance).where(ShareBalance.shareholder_id == shareholder.id))
    balance = bal_result.scalar_one_or_none()
    if balance:
        balance.current_balance = to_decimal(balance.current_balance) - total_amount
        balance.pending_balance = to_decimal(balance.pending_balance) + total_amount

    await db.commit()
    await db.refresh(settlement)
    return settlement


@router.post("/batch")
async def batch_create_settlements(
    req: SettlementBatchCreate,
    current_user: User = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
):
    """批量创建结算单（给多个分账方生成转账清单）"""
    # 确定要结算的分账方
    if req.shareholder_ids:
        shareholder_ids = req.shareholder_ids
    else:
        # 所有有pending余额的分账方
        bal_result = await db.execute(
            select(ShareBalance.shareholder_id).where(ShareBalance.current_balance > 0)
        )
        shareholder_ids = [row[0] for row in bal_result.all()]

    if not shareholder_ids:
        raise HTTPException(status_code=400, detail="没有需要结算的分账方")

    created = []
    for sh_id in shareholder_ids:
        # 查待结算明细
        records = (await db.execute(
            select(ShareRecord).where(ShareRecord.shareholder_id == sh_id, ShareRecord.status == "pending")
        )).scalars().all()
        if not records:
            continue

        sh_result = await db.execute(select(Shareholder).where(Shareholder.id == sh_id))
        shareholder = sh_result.scalar_one_or_none()
        if not shareholder:
            continue

        total_amount = sum(to_decimal(r.actual_amount or r.share_amount) for r in records)

        settlement = Settlement(
            settlement_no=generate_settlement_no(),
            shareholder_id=sh_id,
            shareholder_name=shareholder.name,
            total_records=len(records),
            total_amount=total_amount,
            payment_method=req.payment_method,
            status="pending",
            remark=req.remark,
            created_by=current_user.id,
        )
        db.add(settlement)
        await db.flush()

        for record in records:
            record.settlement_id = settlement.id
            record.status = "settling"

        bal_result = await db.execute(select(ShareBalance).where(ShareBalance.shareholder_id == sh_id))
        balance = bal_result.scalar_one_or_none()
        if balance:
            balance.current_balance = to_decimal(balance.current_balance) - total_amount
            balance.pending_balance = to_decimal(balance.pending_balance) + total_amount

        created.append({"settlement_no": settlement.settlement_no, "shareholder_name": shareholder.name, "amount": float(total_amount)})

    await db.commit()
    return {"success": True, "created_count": len(created), "settlements": created}


@router.post("/{settlement_id}/transfer", response_model=SettlementResponse)
async def mark_transferred(
    settlement_id: int, req: SettlementTransfer,
    current_user: User = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
):
    """登记已转账（你手动微信/支付宝转账后，在系统登记）"""
    result = await db.execute(select(Settlement).where(Settlement.id == settlement_id))
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(status_code=404, detail="结算单不存在")
    if settlement.status != "pending":
        raise HTTPException(status_code=400, detail=f"当前状态({settlement.status})不能登记转账")

    settlement.status = "transferred"
    settlement.transaction_no = req.transaction_no
    settlement.transfer_voucher_url = req.transfer_voucher_url
    settlement.actual_amount = req.actual_amount or settlement.total_amount
    settlement.fee_amount = req.fee_amount or 0
    settlement.transferred_by = current_user.id
    settlement.transferred_at = datetime.now(timezone.utc)
    if req.remark:
        settlement.remark = req.remark

    await db.commit()
    await db.refresh(settlement)
    return settlement


@router.post("/{settlement_id}/confirm", response_model=SettlementResponse)
async def confirm_settlement(
    settlement_id: int, req: Optional[SettlementConfirm] = None,
    current_user: User = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
):
    """确认结算完成"""
    result = await db.execute(select(Settlement).where(Settlement.id == settlement_id))
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(status_code=404, detail="结算单不存在")
    if settlement.status not in ["transferred", "pending"]:
        raise HTTPException(status_code=400, detail=f"当前状态({settlement.status})不能确认")

    settlement.status = "confirmed"
    settlement.confirmed_by = current_user.id
    settlement.confirmed_at = datetime.now(timezone.utc)

    # 更新分账明细状态
    await db.execute(
        update(ShareRecord).where(ShareRecord.settlement_id == settlement_id).values(status="settled", settled_at=datetime.now(timezone.utc))
    )

    # 更新余额
    actual_amount = to_decimal(settlement.actual_amount or settlement.total_amount)
    bal_result = await db.execute(select(ShareBalance).where(ShareBalance.shareholder_id == settlement.shareholder_id))
    balance = bal_result.scalar_one_or_none()
    if balance:
        balance.pending_balance = to_decimal(balance.pending_balance) - to_decimal(settlement.total_amount)
        balance.total_settled = to_decimal(balance.total_settled) + actual_amount
        balance.settled_orders = (balance.settled_orders or 0) + settlement.total_records
        balance.last_settlement_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(settlement)
    return settlement


@router.post("/{settlement_id}/cancel")
async def cancel_settlement(
    settlement_id: int,
    current_user: User = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
):
    """取消结算单（回滚到待结算）"""
    result = await db.execute(select(Settlement).where(Settlement.id == settlement_id))
    settlement = result.scalar_one_or_none()
    if not settlement:
        raise HTTPException(status_code=404, detail="结算单不存在")
    if settlement.status == "confirmed":
        raise HTTPException(status_code=400, detail="已确认的结算单不能取消")

    settlement.status = "cancelled"

    # 回滚分账明细
    await db.execute(
        update(ShareRecord).where(ShareRecord.settlement_id == settlement_id).values(status="pending", settlement_id=None)
    )

    # 回滚余额
    total_amount = to_decimal(settlement.total_amount)
    bal_result = await db.execute(select(ShareBalance).where(ShareBalance.shareholder_id == settlement.shareholder_id))
    balance = bal_result.scalar_one_or_none()
    if balance:
        balance.pending_balance = to_decimal(balance.pending_balance) - total_amount
        balance.current_balance = to_decimal(balance.current_balance) + total_amount

    await db.commit()
    return {"success": True, "message": "结算单已取消"}


@router.get("/transfer-list/export")
async def export_transfer_list(
    status: str = "pending",
    current_user: User = Depends(require_finance),
    db: AsyncSession = Depends(get_db)
):
    """导出现金转账清单（Excel）"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl未安装")

    # 查待转账的结算单
    query = select(Settlement).where(Settlement.status == status)
    settlements = (await db.execute(query)).scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "转账清单"

    # 表头
    headers = ["序号", "结算单号", "分账方姓名", "结算方式", "收款账号", "实名", "转账金额", "备注"]
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    # 数据
    for idx, st in enumerate(settlements, 1):
        # 查分账方收款信息
        sh_result = await db.execute(select(Shareholder).where(Shareholder.id == st.shareholder_id))
        sh = sh_result.scalar_one_or_none()

        account = ""
        real_name = ""
        if st.payment_method == "wechat":
            account = sh.wechat_account if sh else ""
            real_name = sh.wechat_real_name if sh else ""
        elif st.payment_method == "alipay":
            account = sh.alipay_account if sh else ""
            real_name = sh.alipay_real_name if sh else ""
        elif st.payment_method == "bank":
            account = f"{sh.bank_name if sh else ''} {sh.bank_card_no if sh else ''}"
            real_name = sh.bank_account_name if sh else ""

        row = [idx, st.settlement_no, st.shareholder_name, st.payment_method,
               account, real_name, float(st.total_amount), st.remark or ""]
        for col, value in enumerate(row, 1):
            ws.cell(row=idx + 1, column=col, value=value)

    # 列宽
    widths = [6, 22, 15, 10, 25, 12, 12, 20]
    for col, width in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + col)].width = width

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    from urllib.parse import quote
    filename = f"转账清单_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    )


@router.get("/stats/summary")
async def settlement_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """结算统计"""
    total_settlements = (await db.execute(select(func.count(Settlement.id)))).scalar()
    total_amount = (await db.execute(select(func.coalesce(func.sum(Settlement.total_amount), 0)))).scalar()
    pending_count = (await db.execute(select(func.count(Settlement.id)).where(Settlement.status == "pending"))).scalar()
    pending_amount = (await db.execute(select(func.coalesce(func.sum(Settlement.total_amount), 0)).where(Settlement.status == "pending"))).scalar()
    confirmed_count = (await db.execute(select(func.count(Settlement.id)).where(Settlement.status == "confirmed"))).scalar()
    confirmed_amount = (await db.execute(select(func.coalesce(func.sum(Settlement.actual_amount), 0)).where(Settlement.status == "confirmed"))).scalar()

    return {
        "total_settlements": total_settlements,
        "total_amount": float(total_amount),
        "pending_count": pending_count,
        "pending_amount": float(pending_amount),
        "confirmed_count": confirmed_count,
        "confirmed_amount": float(confirmed_amount),
    }
