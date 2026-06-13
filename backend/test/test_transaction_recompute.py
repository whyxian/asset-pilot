"""重算逻辑单元测试 — 用临时 SQLite 数据库验证 recompute_holding 算法的正确性

直接调用 service 层 recompute_holding 函数，不经过 HTTP 接口。
每个测试独立建表 + 灌数据 + 调用 + 断言，互不干扰。

执行：
    .venv/bin/python backend/test/test_transaction_recompute.py
"""

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

# 使用内存数据库做测试（每次测试独立）
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


async def _make_engine():
    """每个测试独立建一个内存库 + 建表"""
    from app.core.database import Base
    # 触发所有 ORM 注册到 Base.metadata
    from app.models.orm.asset_quote_orm import AssetQuoteRecord  # noqa: F401
    from app.models.orm.asset_holding_orm import AssetHoldingRecord
    from app.models.orm.asset_variety_orm import AssetVarietyRecord  # noqa: F401
    from app.models.orm.transaction_orm import TransactionRecord

    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, AssetHoldingRecord, TransactionRecord


async def _seed_holding(session: AsyncSession, HoldingRecord, ticker: str,
                         qty: str, cost: str, total: str, dt: date = date(2024, 1, 1)):
    """种入一条持仓基线（initial_* = quantity = ...）"""
    h = HoldingRecord(
        ticker=ticker,
        name=ticker,
        market="CN",
        asset_class="STOCK",
        currency="CNY",
        quantity=Decimal(qty),
        cost_price=Decimal(cost),
        total_invested=Decimal(total),
        initial_quantity=Decimal(qty),
        initial_cost_price=Decimal(cost),
        initial_total_invested=Decimal(total),
        first_buy_date=dt,
    )
    session.add(h)
    await session.commit()


async def _add_txn(session: AsyncSession, TxnRecord, ticker: str, type_: str,
                    dt: date, qty: str | None = None, price: str | None = None,
                    amount: str | None = None):
    """种入一条交易"""
    t = TxnRecord(
        ticker=ticker,
        transaction_date=dt,
        type=type_,
        quantity=Decimal(qty) if qty else None,
        unit_price=Decimal(price) if price else None,
        amount=Decimal(amount) if amount else None,
    )
    session.add(t)
    await session.commit()


async def _read_holding(session: AsyncSession, HoldingRecord, ticker: str):
    return (await session.execute(
        select(HoldingRecord).where(HoldingRecord.ticker == ticker)
    )).scalar_one()


def _approx(a: Decimal, b: str, tol: str = "0.01") -> bool:
    """容差比较 Decimal"""
    return abs(a - Decimal(b)) <= Decimal(tol)


# ════════════════════════════════════════════════════
# 测试 1：仅基线，无交易 → 派生字段 = 基线
# ════════════════════════════════════════════════════
async def test_baseline_only():
    print("\n[1/5] 仅基线，无交易 → 派生字段保持 = 基线")
    engine, HoldingRecord, _ = await _make_engine()
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # patch async_session 让 recompute_holding 用上测试 engine
    import app.core.database as db_mod
    db_mod.async_session = Session

    from app.services.asset_holding_service import recompute_holding

    async with Session() as session:
        await _seed_holding(session, HoldingRecord, "TEST", "100", "10", "1000")

    async with Session() as session:
        await recompute_holding(session, "TEST")
        await session.commit()

    async with Session() as session:
        h = await _read_holding(session, HoldingRecord, "TEST")
        assert _approx(h.quantity, "100"), f"quantity={h.quantity}"
        assert _approx(h.cost_price, "10"), f"cost_price={h.cost_price}"
        assert _approx(h.total_invested, "1000"), f"total_invested={h.total_invested}"
    print("    ✅ quantity=100 cost_price=10 total_invested=1000")
    await engine.dispose()


# ════════════════════════════════════════════════════
# 测试 2：基线 + 一笔买入 → 加权平均
# ════════════════════════════════════════════════════
async def test_buy_after_baseline():
    print("\n[2/5] 基线 100@10 + buy 50@12 → quantity=150, cost_price≈10.667")
    engine, HoldingRecord, TxnRecord = await _make_engine()
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    import app.core.database as db_mod
    db_mod.async_session = Session
    from app.services.asset_holding_service import recompute_holding

    async with Session() as session:
        await _seed_holding(session, HoldingRecord, "TEST", "100", "10", "1000")
        await _add_txn(session, TxnRecord, "TEST", "buy", date(2024, 2, 1),
                        qty="50", price="12", amount="600")

    async with Session() as session:
        await recompute_holding(session, "TEST")
        await session.commit()

    async with Session() as session:
        h = await _read_holding(session, HoldingRecord, "TEST")
        assert _approx(h.quantity, "150"), f"quantity={h.quantity}"
        assert _approx(h.total_invested, "1600"), f"total_invested={h.total_invested}"
        assert _approx(h.cost_price, "10.667"), f"cost_price={h.cost_price}"
    print(f"    ✅ quantity={h.quantity} cost_price={h.cost_price} total_invested={h.total_invested}")
    await engine.dispose()


# ════════════════════════════════════════════════════
# 测试 3：买入后卖出 — 加权平均法（cost_price 不变，total 按比例减）
# ════════════════════════════════════════════════════
async def test_sell_weighted_average():
    print("\n[3/5] 100@10 → +50@12 → -30 → quantity=120, cost_price不变, total按比例减")
    engine, HoldingRecord, TxnRecord = await _make_engine()
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    import app.core.database as db_mod
    db_mod.async_session = Session
    from app.services.asset_holding_service import recompute_holding

    async with Session() as session:
        await _seed_holding(session, HoldingRecord, "TEST", "100", "10", "1000")
        await _add_txn(session, TxnRecord, "TEST", "buy", date(2024, 2, 1),
                        qty="50", price="12", amount="600")
        await _add_txn(session, TxnRecord, "TEST", "sell", date(2024, 3, 1),
                        qty="30", price="15")

    async with Session() as session:
        await recompute_holding(session, "TEST")
        await session.commit()

    async with Session() as session:
        h = await _read_holding(session, HoldingRecord, "TEST")
        # 买入后：q=150, p≈10.6667, t=1600
        # 卖出 30：q=120, p 不变 ≈10.6667, t = 1600 - 10.6667 * 30 ≈ 1280
        assert _approx(h.quantity, "120"), f"quantity={h.quantity}"
        assert _approx(h.cost_price, "10.667"), f"cost_price={h.cost_price}"
        assert _approx(h.total_invested, "1280"), f"total_invested={h.total_invested}"
    print(f"    ✅ quantity={h.quantity} cost_price={h.cost_price} total_invested={h.total_invested}")
    await engine.dispose()


# ════════════════════════════════════════════════════
# 测试 4：卖超 → 抛 BusinessError
# ════════════════════════════════════════════════════
async def test_oversell_raises():
    print("\n[4/5] 100@10 → 卖出 200 → 抛 BusinessError")
    engine, HoldingRecord, TxnRecord = await _make_engine()
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    import app.core.database as db_mod
    db_mod.async_session = Session
    from app.services.asset_holding_service import recompute_holding
    from app.core.exceptions import BusinessError

    async with Session() as session:
        await _seed_holding(session, HoldingRecord, "TEST", "100", "10", "1000")
        await _add_txn(session, TxnRecord, "TEST", "sell", date(2024, 2, 1),
                        qty="200", price="12")

    raised = False
    async with Session() as session:
        try:
            await recompute_holding(session, "TEST")
        except BusinessError as e:
            raised = True
            print(f"    ✅ 已抛 BusinessError: {e.message}")
    assert raised, "应当抛 BusinessError 但没有"
    await engine.dispose()


# ════════════════════════════════════════════════════
# 测试 5：清仓 → quantity=0, cost_price=0, total=0
# ════════════════════════════════════════════════════
async def test_full_liquidation():
    print("\n[5/5] 100@10 → 卖出 100 → 清仓后 quantity=0 cost_price=0 total=0")
    engine, HoldingRecord, TxnRecord = await _make_engine()
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    import app.core.database as db_mod
    db_mod.async_session = Session
    from app.services.asset_holding_service import recompute_holding

    async with Session() as session:
        await _seed_holding(session, HoldingRecord, "TEST", "100", "10", "1000")
        await _add_txn(session, TxnRecord, "TEST", "sell", date(2024, 2, 1),
                        qty="100", price="15")

    async with Session() as session:
        await recompute_holding(session, "TEST")
        await session.commit()

    async with Session() as session:
        h = await _read_holding(session, HoldingRecord, "TEST")
        assert _approx(h.quantity, "0"), f"quantity={h.quantity}"
        assert _approx(h.cost_price, "0"), f"cost_price={h.cost_price}"
        assert _approx(h.total_invested, "0"), f"total_invested={h.total_invested}"
    print(f"    ✅ quantity={h.quantity} cost_price={h.cost_price} total_invested={h.total_invested}")
    await engine.dispose()


async def main():
    print("=" * 60)
    print("recompute_holding 单元测试")
    print("=" * 60)
    await test_baseline_only()
    await test_buy_after_baseline()
    await test_sell_weighted_average()
    await test_oversell_raises()
    await test_full_liquidation()
    print("\n" + "=" * 60)
    print("✅ 全部 5 个测试通过")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
