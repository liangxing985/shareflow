"""支付模块API（码支付风格）
- POST /payment/create - 创建支付订单（MD5签名验证）
- GET /payment/status/{order_no} - 查询支付状态（公开接口）
"""
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import settings
from app.database import get_db
from app.models.order import Order
from app.models.payment_account import PaymentAccount
from app.core.signature import verify_sign_with_keys
from app.core.audit_log import log_operation

router = APIRouter(prefix="/payment", tags=["支付对接"])

# 时间戳有效窗口（秒），防止重放攻击
TIMESTAMP_VALID_WINDOW = 300  # 5分钟


def generate_order_no() -> str:
    """生成订单号（时间戳+随机后缀，防止高并发重复）"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = secrets.token_hex(3).upper()  # 6位随机十六进制
    return f"SF{timestamp}{random_suffix}"


async def get_default_qr_codes(db: AsyncSession) -> dict:
    """获取默认的微信和支付宝收款码URL"""
    result = {"wechat": "", "alipay": ""}

    # 查询启用的收款账户
    accounts = await db.execute(
        select(PaymentAccount).where(PaymentAccount.status == "active")
    )
    account_list = accounts.scalars().all()

    # 优先用默认账户
    for acc in account_list:
        if acc.is_default:
            if acc.platform == "wechat" and not result["wechat"]:
                result["wechat"] = acc.qr_code_url or ""
            elif acc.platform == "alipay" and not result["alipay"]:
                result["alipay"] = acc.qr_code_url or ""

    # 补充非默认账户
    for acc in account_list:
        if not acc.is_default:
            if acc.platform == "wechat" and not result["wechat"]:
                result["wechat"] = acc.qr_code_url or ""
            elif acc.platform == "alipay" and not result["alipay"]:
                result["alipay"] = acc.qr_code_url or ""

    return result


def _validate_timestamp(timestamp_str: str) -> tuple[bool, str]:
    """
    验证时间戳是否在有效窗口内（防止重放攻击）
    返回 (是否有效, 错误信息)
    """
    try:
        timestamp = int(timestamp_str)
    except (ValueError, TypeError):
        return False, "时间戳格式错误"

    now = int(datetime.now().timestamp())
    if abs(now - timestamp) > TIMESTAMP_VALID_WINDOW:
        return False, f"时间戳已过期（有效窗口{TIMESTAMP_VALID_WINDOW}秒）"

    return True, ""


@router.post("/create")
async def payment_create(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    创建支付订单（码支付风格）
    - MD5签名验证
    - 时间戳验证（防重放攻击）
    - 返回支付链接和收款码URL
    """
    client_ip = request.client.host if request.client else ""

    # 解析请求体
    try:
        params = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体格式错误")

    if not isinstance(params, dict):
        return {"code": -1, "msg": "请求体必须是JSON对象", "data": None}

    # 必填参数校验
    required_fields = ["app_id", "out_order_no", "total_amount", "product_name", "timestamp", "sign"]
    for field in required_fields:
        if field not in params or not params[field]:
            return {"code": -1, "msg": f"缺少必填参数: {field}", "data": None}

    # 时间戳验证（防止重放攻击）
    valid, error_msg = _validate_timestamp(str(params["timestamp"]))
    if not valid:
        return {"code": -1, "msg": error_msg, "data": None}

    # 签名验证
    if settings.PAYMENT_SIGN_ENABLED:
        if not settings.api_keys_list:
            return {"code": -1, "msg": "服务器未配置API Key", "data": None}
        if not verify_sign_with_keys(params, settings.api_keys_list):
            logger.warning(f"支付创建签名验证失败，IP: {client_ip}")
            return {"code": -1, "msg": "签名验证失败", "data": None}

    # 校验app_id
    if str(params.get("app_id")) != settings.PAYMENT_APP_ID:
        return {"code": -1, "msg": f"app_id不匹配", "data": None}

    # 校验金额（用Decimal，避免float精度问题）
    try:
        total_amount = Decimal(str(params["total_amount"]))
        if total_amount <= 0:
            return {"code": -1, "msg": "金额必须大于0", "data": None}
        if total_amount > Decimal("1000000"):  # 最大100万
            return {"code": -1, "msg": "金额超过上限", "data": None}
    except (InvalidOperation, ValueError, TypeError):
        return {"code": -1, "msg": "金额格式错误", "data": None}

    # 校验字符串长度（防止数据库溢出和XSS）
    out_order_no = str(params["out_order_no"])[:64]
    product_name = str(params["product_name"])[:200]
    payer_name = str(params.get("payer_name", ""))[:100]
    payer_contact = str(params.get("payer_contact", ""))[:100]
    product_desc = str(params.get("product_desc", ""))[:1000]
    category = str(params.get("category", ""))[:50]
    remark = str(params.get("remark", ""))[:500]

    # 检查外部订单号重复
    exist = await db.execute(
        select(Order).where(Order.out_order_no == out_order_no)
    )
    if exist.scalar_one_or_none():
        return {"code": -1, "msg": "外部订单号已存在", "data": None}

    # 创建订单（待支付状态，5分钟过期）
    pay_expire_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    order = Order(
        order_no=generate_order_no(),
        out_order_no=out_order_no,
        total_amount=total_amount,
        payer_name=payer_name,
        payer_contact=payer_contact,
        product_name=product_name,
        product_desc=product_desc,
        category=category,
        pay_status="pending_pay",
        pay_expire_at=pay_expire_at,
        remark=remark,
        source="api",
        api_app_id=str(params.get("app_id", "")),
    )
    db.add(order)
    await db.flush()

    await log_operation(
        db, None, "payment_create", "order", order.id,
        f"支付模块创建订单 {order.order_no}，金额 {total_amount}，外部订单号 {out_order_no}，IP: {client_ip}",
        client_ip
    )
    await db.commit()
    await db.refresh(order)

    # 获取收款码URL
    qr_codes = await get_default_qr_codes(db)

    # 构造支付链接
    pay_url = f"/pay/{order.order_no}"

    # 返回码支付风格响应
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "order_no": order.order_no,
            "out_order_no": order.out_order_no,
            "total_amount": f"{float(order.total_amount):.2f}",
            "pay_url": pay_url,
            "qr_code_urls": qr_codes,
            "expire_at": pay_expire_at.strftime("%Y-%m-%d %H:%M:%S"),
            "pay_status": order.pay_status,
        }
    }


@router.get("/status/{order_no}")
async def payment_status(
    order_no: str,
    db: AsyncSession = Depends(get_db)
):
    """
    查询支付状态（公开接口，前端轮询用）
    """
    # 校验订单号格式（防止SQL注入和路径遍历）
    if not order_no or len(order_no) > 64 or not order_no.isalnum():
        return {"code": -1, "msg": "订单号格式错误", "data": None}

    # 查询订单
    result = await db.execute(
        select(Order).where(Order.order_no == order_no)
    )
    order = result.scalar_one_or_none()

    if not order:
        return {"code": -1, "msg": "订单不存在", "data": None}

    # 检查是否过期
    if order.pay_status == "pending_pay" and order.pay_expire_at:
        if datetime.now(timezone.utc) > order.pay_expire_at:
            order.pay_status = "expired"
            await db.commit()

    return {
        "code": 0,
        "msg": "success",
        "data": {
            "order_no": order.order_no,
            "out_order_no": order.out_order_no or "",
            "total_amount": f"{float(order.total_amount):.2f}",
            "pay_status": order.pay_status,
            "paid_at": order.paid_at.strftime("%Y-%m-%d %H:%M:%S") if order.paid_at else "",
            "expire_at": order.pay_expire_at.strftime("%Y-%m-%d %H:%M:%S") if order.pay_expire_at else "",
        }
    }
