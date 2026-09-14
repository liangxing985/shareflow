"""ShareFlow 分账系统 - 主应用"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from app.config import settings
from app.database import init_db
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时校验安全密钥
    settings.validate_security_keys()
    if settings.ENV == "production" and settings.CORS_ORIGINS == "*":
        logger.warning("⚠️  生产环境CORS配置为*，建议配置具体域名以提高安全性")

    logger.info(f"{settings.APP_NAME} 启动中...")
    await init_db()
    logger.info("数据库初始化完成")
    logger.info(f"{settings.APP_NAME} 启动完成，版本: {settings.APP_VERSION}")
    yield
    logger.info(f"{settings.APP_NAME} 关闭")


# 生产环境关闭API文档
docs_kwargs = {}
if settings.ENV == "production" and not settings.DEBUG:
    docs_kwargs = {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="个人收款 + 记账式分账系统，支持微信/支付宝收款、多级分账、批量结算、对账管理",
    lifespan=lifespan,
    **docs_kwargs,
)

# CORS（生产环境建议配置具体域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理器 - 生产环境不泄露内部错误信息
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"未处理的异常: {exc}")
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "type": type(exc).__name__},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试或联系管理员"},
    )


# 路由
app.include_router(api_router)

# 静态文件服务（上传的图片/文件）
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "(生产环境已关闭)",
        "api_prefix": "/api/v1",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
