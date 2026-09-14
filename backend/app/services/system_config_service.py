"""系统配置服务"""
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.system_config import SystemConfig
from app.config import settings


# 默认配置项定义
DEFAULT_CONFIGS = {
    "payment_app_id": {
        "value": settings.PAYMENT_APP_ID,
        "type": "string",
        "description": "商户ID/AppID，支付对接用"
    },
    "api_keys": {
        "value": settings.API_KEYS,
        "type": "string",
        "description": "API Key（通信密钥），多个用逗号分隔"
    },
    "payment_notify_url": {
        "value": settings.PAYMENT_NOTIFY_URL,
        "type": "string",
        "description": "支付成功回调地址（你的业务系统接收回调的URL）"
    },
    "payment_notify_retry_max": {
        "value": str(settings.PAYMENT_NOTIFY_RETRY_MAX),
        "type": "int",
        "description": "回调失败最大重试次数"
    },
    "payment_sign_enabled": {
        "value": "true" if settings.PAYMENT_SIGN_ENABLED else "false",
        "type": "bool",
        "description": "是否启用签名验证（生产环境必须开启）"
    },
}


class SystemConfigService:
    """系统配置服务"""

    @staticmethod
    async def init_default_configs(db: AsyncSession):
        """初始化默认配置（启动时调用，不存在则插入）"""
        for key, config in DEFAULT_CONFIGS.items():
            exist = await db.execute(
                select(SystemConfig).where(SystemConfig.config_key == key)
            )
            if not exist.scalar_one_or_none():
                new_config = SystemConfig(
                    config_key=key,
                    config_value=config["value"],
                    config_type=config["type"],
                    description=config["description"]
                )
                db.add(new_config)
                logger.info(f"初始化系统配置: {key} = {config['value']}")
        await db.commit()

    @staticmethod
    async def get_all_configs(db: AsyncSession) -> Dict[str, Any]:
        """获取所有配置（返回字典）"""
        result = await db.execute(select(SystemConfig))
        configs = result.scalars().all()

        config_dict = {}
        for config in configs:
            config_dict[config.config_key] = SystemConfigService._parse_value(
                config.config_value, config.config_type
            )
        return config_dict

    @staticmethod
    async def get_config(db: AsyncSession, key: str, default: Any = None) -> Any:
        """获取单个配置"""
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        config = result.scalar_one_or_none()
        if not config:
            return default
        return SystemConfigService._parse_value(config.config_value, config.config_type)

    @staticmethod
    async def update_configs(db: AsyncSession, updates: Dict[str, Any]) -> bool:
        """批量更新配置"""
        for key, value in updates.items():
            result = await db.execute(
                select(SystemConfig).where(SystemConfig.config_key == key)
            )
            config = result.scalar_one_or_none()
            if config:
                config.config_value = str(value)
                logger.info(f"更新系统配置: {key} = {value}")
        await db.commit()
        return True

    @staticmethod
    def _parse_value(value: Optional[str], config_type: str) -> Any:
        """根据类型解析配置值"""
        if value is None:
            return None
        if config_type == "int":
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        if config_type == "bool":
            return str(value).lower() in ("true", "1", "yes")
        if config_type == "json":
            try:
                import json
                return json.loads(value)
            except Exception:
                return {}
        return value


system_config_service = SystemConfigService()
