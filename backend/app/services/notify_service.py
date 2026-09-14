"""支付回调通知服务（含重试机制）"""
import asyncio
import ipaddress
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from loguru import logger
import httpx

from app.config import settings
from app.core.signature import generate_sign


class NotifyService:
    """支付回调通知服务"""

    # 重试间隔（秒）：第1次失败后等60秒，第2次等300秒，第3次等600秒
    RETRY_INTERVALS = [60, 300, 600]

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """
        校验回调地址是否安全（防止SSRF）
        - 只允许http和https协议
        - 禁止内网IP、回环地址、链路本地地址
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                logger.warning(f"回调地址协议不允许: {parsed.scheme}")
                return False

            hostname = parsed.hostname
            if not hostname:
                return False

            # 检查是否是IP地址
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    logger.warning(f"回调地址禁止使用内网IP: {hostname}")
                    return False
            except ValueError:
                # 不是IP地址，是域名，允许通过（域名可能解析到内网IP，但这是可接受的风险）
                pass

            return True
        except Exception as e:
            logger.warning(f"回调地址校验异常: {e}")
            return False

    @staticmethod
    def _extract_order_data(order: any) -> dict:
        """
        从订单对象中提取回调需要的数据（避免后台任务访问detached对象）
        """
        return {
            "order_no": str(order.order_no),
            "out_order_no": str(order.out_order_no or ""),
            "total_amount": f"{float(order.total_amount):.2f}",
            "paid_at": order.paid_at.strftime("%Y-%m-%d %H:%M:%S") if order.paid_at else "",
            "transaction_id": str(order.transaction_id or ""),
        }

    @staticmethod
    async def send_payment_notify(
        order_data: dict,
        notify_url: Optional[str] = None,
        api_key: Optional[str] = None,
        app_id: Optional[str] = None
    ) -> bool:
        """
        发送支付成功回调通知
        带重试机制，最多重试 PAYMENT_NOTIFY_RETRY_MAX 次
        注意：order_data 必须是预提取的字典，不能是SQLAlchemy对象
        """
        # 确定回调地址
        url = notify_url or settings.PAYMENT_NOTIFY_URL
        if not url:
            logger.warning(f"订单 {order_data.get('order_no')} 未配置回调地址，跳过回调")
            return False

        # SSRF校验
        if not NotifyService._is_safe_url(url):
            logger.error(f"订单 {order_data.get('order_no')} 回调地址不安全，拒绝发送: {url}")
            return False

        # 确定API Key（用于签名）
        key = api_key
        if not key and settings.api_keys_list:
            key = settings.api_keys_list[0]
        if not key:
            logger.warning(f"订单 {order_data.get('order_no')} 未配置API Key，回调不签名")

        # 确定app_id
        payment_app_id = app_id or settings.PAYMENT_APP_ID

        # 构造回调参数（只包含必要字段，不暴露内部财务数据）
        params = {
            "app_id": payment_app_id,
            "order_no": order_data["order_no"],
            "out_order_no": order_data["out_order_no"],
            "total_amount": order_data["total_amount"],
            "pay_status": "paid",
            "paid_at": order_data["paid_at"],
            "transaction_id": order_data["transaction_id"],
            "timestamp": int(datetime.now().timestamp()),
        }

        # 生成签名
        if key:
            params["sign"] = generate_sign(params, key)

        # 发送回调（带重试）
        max_retries = settings.PAYMENT_NOTIFY_RETRY_MAX
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"发送支付回调 [{attempt+1}/{max_retries+1}] 订单={order_data['order_no']} -> {url}")

                async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
                    response = await client.post(
                        url,
                        json=params,
                        headers={"Content-Type": "application/json"}
                    )

                    # 解析响应
                    try:
                        result = response.json()
                    except Exception:
                        result = {"raw": response.text[:500]}  # 限制长度，防止日志过大

                    # 判断是否成功（code=0 或 返回success）
                    is_success = False
                    if isinstance(result, dict):
                        if result.get("code") == 0:
                            is_success = True
                        elif str(result.get("msg", "")).lower() in ("success", "ok"):
                            is_success = True
                    elif response.status_code == 200 and "success" in str(result).lower():
                        is_success = True

                    if is_success:
                        logger.info(f"支付回调成功 订单={order_data['order_no']}")
                        return True
                    else:
                        logger.warning(f"支付回调返回失败 订单={order_data['order_no']}, 状态码={response.status_code}")

            except httpx.TimeoutException:
                logger.warning(f"支付回调超时 订单={order_data['order_no']}")
            except Exception as e:
                logger.error(f"支付回调异常 订单={order_data['order_no']}, 错误={str(e)[:200]}")

            # 重试等待
            if attempt < max_retries:
                wait_time = NotifyService.RETRY_INTERVALS[attempt] if attempt < len(NotifyService.RETRY_INTERVALS) else 600
                logger.info(f"等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)

        logger.error(f"支付回调最终失败 订单={order_data['order_no']}, 已重试{max_retries}次")
        return False

    @staticmethod
    def send_payment_notify_background(
        order_data: dict,
        notify_url: Optional[str] = None,
        api_key: Optional[str] = None,
        app_id: Optional[str] = None
    ):
        """
        后台发送支付回调（不阻塞主流程）
        使用asyncio.create_task在后台执行
        注意：order_data 必须是预提取的字典，不能是SQLAlchemy对象
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(
                    NotifyService.send_payment_notify(order_data, notify_url, api_key, app_id)
                )
            else:
                # 如果没有运行中的事件循环，用新线程执行
                import threading
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    new_loop.run_until_complete(
                        NotifyService.send_payment_notify(order_data, notify_url, api_key, app_id)
                    )
                    new_loop.close()
                threading.Thread(target=run_in_thread, daemon=True).start()
        except Exception as e:
            logger.error(f"创建后台回调任务失败: {str(e)[:200]}")


notify_service = NotifyService()
