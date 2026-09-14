"""数据库连接"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


# SQLite不支持pool_size参数，需要条件设置
_engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库表"""
    from app.models import user, payment_account, order, shareholder, share_rule, share_record, share_balance, settlement, reconciliation, operation_log
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
