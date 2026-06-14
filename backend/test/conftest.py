"""共享 pytest fixture — 内存 SQLite + monkey patch async_session

每个测试都获得一个独立的 in-memory SQLite 引擎,fixture 自动:
1. 建表 (触发所有 ORM 注册到 Base.metadata)
2. 替换 app.core.database.async_session 为指向测试引擎的 sessionmaker
3. 测试结束后销毁引擎

使用：
    async def test_something(Session, seed_variety):
        await seed_variety(ticker="TEST")
        async with Session() as s:
            ...
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine():
    """每个测试独立的内存 SQLite 引擎,自动建好全部表"""
    from app.core.database import Base
    # 触发所有 ORM 注册
    from app.models.orm.asset_quote_orm import AssetQuoteRecord  # noqa: F401
    from app.models.orm.asset_holding_orm import AssetHoldingRecord  # noqa: F401
    from app.models.orm.asset_variety_orm import AssetVarietyRecord  # noqa: F401
    from app.models.orm.transaction_orm import TransactionRecord  # noqa: F401
    from app.models.orm.closed_holding_orm import ClosedHoldingRecord, ClosedTransactionRecord  # noqa: F401

    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def Session(engine, monkeypatch):
    """sessionmaker 绑定测试引擎；同时把所有引用了 async_session 的模块都替换掉

    因为很多 service / repository 在模块加载时已经
    `from app.core.database import async_session` 把绑定固化了,
    单纯改 app.core.database.async_session 不够 — 需要把所有
    引用了它的模块的 async_session 属性也覆盖。
    """
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    # 主源
    monkeypatch.setattr("app.core.database.async_session", Session)
    # 已 from import 的模块都打补丁
    for mod_path in (
        "app.repositories.asset_holding_repository",
        "app.repositories.transaction_repository",
        "app.repositories.asset_quote_repository",
        "app.repositories.asset_variety_repository",
        "app.repositories.closed_holding_repository",
        "app.services.asset_holding_service",
        "app.services.transaction_service",
        "app.services.asset_quote_service",
        "app.services.asset_variety_service",
        "app.services.closed_holding_service",
        "app.services.overview_service",
    ):
        try:
            __import__(mod_path)
            monkeypatch.setattr(f"{mod_path}.async_session", Session, raising=False)
        except (ImportError, AttributeError):
            pass
    return Session


@pytest.fixture
async def seed_variety(Session):
    """工具：往 asset_varieties 灌一条品种(用于持仓 create 时通过 variety 校验)"""
    from app.models.orm.asset_variety_orm import AssetVarietyRecord

    async def _seed(
        ticker: str = "TEST",
        asset_class: str = "STOCK",
        market: str = "CN",
        name: str = "测试品种",
        currency: str = "CNY",
    ):
        async with Session() as s:
            s.add(AssetVarietyRecord(
                ticker=ticker,
                name=name,
                asset_class=asset_class,
                market=market,
                currency=currency,
                is_active=True,
            ))
            await s.commit()

    return _seed


@pytest.fixture
async def seed_holding(Session, seed_variety):
    """工具：建一条持仓(同时确保对应品种存在),initial_* = 当前 quantity/cost/total"""
    from app.models.orm.asset_holding_orm import AssetHoldingRecord

    async def _seed(
        ticker: str = "TEST",
        qty: str = "100",
        cost: str = "10",
        total: str = "1000",
        dt: date = date(2024, 1, 1),
        asset_class: str = "STOCK",
        market: str = "CN",
        ensure_variety: bool = True,
    ):
        if ensure_variety:
            await seed_variety(ticker=ticker, asset_class=asset_class, market=market)
        async with Session() as s:
            h = AssetHoldingRecord(
                ticker=ticker,
                name=ticker,
                market=market,
                asset_class=asset_class,
                currency="CNY",
                quantity=Decimal(qty),
                cost_price=Decimal(cost),
                total_invested=Decimal(total),
                initial_quantity=Decimal(qty),
                initial_cost_price=Decimal(cost),
                initial_total_invested=Decimal(total),
                first_buy_date=dt,
            )
            s.add(h)
            await s.commit()

    return _seed


@pytest.fixture
async def add_txn(Session):
    """工具：往 transactions 表插一条交易"""
    from app.models.orm.transaction_orm import TransactionRecord

    async def _add(
        ticker: str,
        type_: str,
        dt: date,
        qty: str | None = None,
        price: str | None = None,
        amount: str | None = None,
        asset_class: str = "STOCK",
        market: str = "CN",
    ):
        async with Session() as s:
            t = TransactionRecord(
                ticker=ticker,
                asset_class=asset_class,
                market=market,
                transaction_date=dt,
                type=type_,
                quantity=Decimal(qty) if qty else None,
                unit_price=Decimal(price) if price else None,
                amount=Decimal(amount) if amount else None,
            )
            s.add(t)
            await s.commit()

    return _add


@pytest.fixture
def read_holding(Session):
    """工具：按三元组读 holdings 当前状态"""
    from app.models.orm.asset_holding_orm import AssetHoldingRecord

    async def _read(ticker: str = "TEST", asset_class: str = "STOCK", market: str = "CN"):
        async with Session() as s:
            return (await s.execute(
                select(AssetHoldingRecord).where(
                    AssetHoldingRecord.ticker == ticker,
                    AssetHoldingRecord.asset_class == asset_class,
                    AssetHoldingRecord.market == market,
                )
            )).scalar_one_or_none()

    return _read


def approx(a, b: str, tol: str = "0.01") -> bool:
    """容差比较 Decimal(测试断言用)"""
    return abs(Decimal(str(a)) - Decimal(b)) <= Decimal(tol)
