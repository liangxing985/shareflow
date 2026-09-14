"""系统配置API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from loguru import logger

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.system_config import SystemConfig
from app.services.system_config_service import system_config_service
from app.core.audit_log import log_operation

router = APIRouter(prefix="/system-config", tags=["系统配置"])


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    configs: Dict[str, Any]


@router.get("")
async def get_system_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有系统配置（仅admin和manager可访问）"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="无权限访问")

    result = await db.execute(select(SystemConfig).order_by(SystemConfig.id))
    configs = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "key": c.config_key,
                "value": system_config_service._parse_value(c.config_value, c.config_type),
                "type": c.config_type,
                "description": c.description
            }
            for c in configs
        ]
    }


@router.put("")
async def update_system_configs(
    req: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新系统配置（仅admin可访问）"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可修改配置")

    # 允许修改的配置键白名单
    allowed_keys = {
        "payment_app_id", "api_keys", "payment_notify_url",
        "payment_notify_retry_max", "payment_sign_enabled"
    }

    # 过滤不允许修改的键
    updates = {k: v for k, v in req.configs.items() if k in allowed_keys}

    if not updates:
        raise HTTPException(status_code=400, detail="没有可更新的配置项")

    # 校验配置值
    for key, value in updates.items():
        if key == "payment_notify_retry_max":
            try:
                retry = int(value)
                if retry < 0 or retry > 10:
                    raise HTTPException(status_code=400, detail="重试次数必须在0-10之间")
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="重试次数必须是数字")

        if key == "payment_app_id" and (not value or len(str(value)) > 64):
            raise HTTPException(status_code=400, detail="商户ID不能为空且不超过64字符")

    # 更新配置
    await system_config_service.update_configs(db, updates)

    # 记录操作日志
    await log_operation(
        db, current_user, "update_system_config", "system_config", 0,
        f"更新系统配置: {', '.join(updates.keys())}"
    )

    logger.info(f"用户 {current_user.username} 更新了系统配置: {list(updates.keys())}")

    return {"success": True, "message": "配置更新成功"}
