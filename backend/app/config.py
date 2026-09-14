"""应用配置"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "ShareFlow 分账系统"
    APP_VERSION: str = "1.1.0"
    DEBUG: bool = False
    ENV: str = "production"  # production / development

    # 数据库
    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/shareflow?charset=utf8mb4"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 安全
    SECRET_KEY: str = ""
    ENCRYPTION_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS（生产环境必须配置具体域名，不要用*）
    CORS_ORIGINS: str = "*"  # 多个域名用逗号分隔，如 "https://a.com,https://b.com"

    # API接入鉴权（业务系统对接用的API Key，多个用逗号分隔）
    API_KEYS: str = ""

    # 文件上传
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # 速率限制
    RATE_LIMIT_ENABLED: bool = True
    LOGIN_MAX_ATTEMPTS: int = 5  # 登录最大失败次数
    LOGIN_LOCK_MINUTES: int = 15  # 锁定时间（分钟）

    # 平台抽成默认配置
    DEFAULT_PLATFORM_FEE_RATE: float = 0.10  # 默认平台抽成10%

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def api_keys_list(self) -> List[str]:
        if not self.API_KEYS:
            return []
        return [k.strip() for k in self.API_KEYS.split(",") if k.strip()]

    def validate_security_keys(self):
        """启动时校验安全密钥，生产环境必须配置"""
        if self.ENV == "production":
            if not self.SECRET_KEY or len(self.SECRET_KEY) < 16:
                raise RuntimeError(
                    "生产环境必须配置 SECRET_KEY（至少16位），请在.env中设置。"
                    "生成方式: openssl rand -hex 32"
                )
            if not self.ENCRYPTION_KEY or len(self.ENCRYPTION_KEY) < 16:
                raise RuntimeError(
                    "生产环境必须配置 ENCRYPTION_KEY（至少16位），请在.env中设置。"
                    "生成方式: openssl rand -hex 32"
                )


settings = Settings()
