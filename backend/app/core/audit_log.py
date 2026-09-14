"""操作日志记录工具"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.operation_log import OperationLog
from app.models.user import User


async def log_operation(
    db: AsyncSession,
    user: Optional[User],
    action: str,
    target_type: str = "",
    target_id: Optional[int] = None,
    detail: str = "",
    ip: str = "",
):
    """
    记录操作日志
    :param db: 数据库会话
    :param user: 操作用户
    :param action: 操作类型（如 create_order, confirm_settlement, delete_user）
    :param target_type: 目标类型（order, settlement, user, shareholder, rule）
    :param target_id: 目标ID
    :param detail: 详细信息
    :param ip: 客户端IP
    """
    try:
        log = OperationLog(
            user_id=user.id if user else None,
            username=user.username if user else "system",
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail[:500] if detail else "",
            ip=ip,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.flush()
    except Exception as e:
        # 日志记录失败不影响主流程
        import logging
        logging.getLogger(__name__).error(f"记录操作日志失败: {e}")
