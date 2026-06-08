"""数据库引擎与会话管理"""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# 数据库文件路径
DB_PATH = Path(__file__).resolve().parents[3] / "data" / "database" / "assetpilot.db"
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    async with async_session() as session:
        yield session


async def init_db():
    """创建所有表"""
    async with engine.begin() as conn:
        from app.models.asset_quote_orm import AssetQuoteRecord  # noqa: F401
        from app.models.asset_holding_orm import AssetHoldingRecord  # noqa: F401
        from app.models.asset_variety_orm import AssetVarietyRecord  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
