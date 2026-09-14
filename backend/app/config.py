"""应用配置"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "ShareFlow 分账系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 数据库
    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/shareflow?charset=utf8mb4"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 安全
    SECRET_KEY: str = "change-me-to-a-random-secret-key-at-least-32-chars"
    ENCRYPTION_KEY: str = "change-me-to-a-random-encryption-key-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 平台抽成默认配置
    DEFAULT_PLATFORM_FEE_RATE: float = 0.10  # 默认平台抽成10%

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
