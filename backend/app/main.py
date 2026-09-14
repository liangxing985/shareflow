"""ShareFlow 分账系统 - 主应用"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from app.config import settings
from app.database import init_db
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info(f"{settings.APP_NAME} 启动中...")
    await init_db()
    logger.info("数据库初始化完成")
    logger.info(f"{settings.APP_NAME} 启动完成，版本: {settings.APP_VERSION}")
    yield
    logger.info(f"{settings.APP_NAME} 关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="个人收款 + 记账式分账系统，支持微信/支付宝收款、多级分账、批量结算、对账管理",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(api_router)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_prefix": "/api/v1",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
