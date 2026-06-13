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
    from app.models.orm.closed_holding_orm import ClosedHoldingRecord, ClosedTransactionRecord  # noqa: F401

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
    print("\n[1/8] 仅基线，无交易 → 派生字段保持 = 基线")
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
    print("\n[2/8] 基线 100@10 + buy 50@12 → quantity=150, cost_price≈10.667")
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
# 测试 3：买入后卖出 — 降低成本法（sell 成交金额冲减总成本）
# ════════════════════════════════════════════════════
async def test_sell_lowers_cost():
    print("\n[3/8] 100@10 → +50@12 → -30@15 → q=120, t=1150, cost≈9.583（做 T 降低成本）")
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
        # 买完 50@12 后：q=150, t=1600, p≈10.667
        # 卖 30@15：t = 1600 - 15×30 = 1150；p = 1150/120 ≈ 9.583
        assert _approx(h.quantity, "120"), f"quantity={h.quantity}"
        assert _approx(h.total_invested, "1150"), f"total_invested={h.total_invested}"
        assert _approx(h.cost_price, "9.583"), f"cost_price={h.cost_price}"
    print(f"    ✅ quantity={h.quantity} cost_price={h.cost_price} total_invested={h.total_invested}")
    await engine.dispose()


# ════════════════════════════════════════════════════
# 测试 4：卖超 → 抛 BusinessError
# ════════════════════════════════════════════════════
async def test_oversell_raises():
    print("\n[4/8] 100@10 → 卖出 200 → 抛 BusinessError")
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
# 测试 5：清仓 → quantity=0, cost_price=0, total=0, liquidated_at = 最后 sell 日期
# ════════════════════════════════════════════════════
async def test_full_liquidation():
    print("\n[5/8] 100@10 → 卖出 100 → 清仓后 q=0 + liquidated_at=sell 日期")
    engine, HoldingRecord, TxnRecord = await _make_engine()
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    import app.core.database as db_mod
    db_mod.async_session = Session
    from app.services.asset_holding_service import recompute_holding

    sell_date = date(2024, 2, 1)
    async with Session() as session:
        await _seed_holding(session, HoldingRecord, "TEST", "100", "10", "1000")
        await _add_txn(session, TxnRecord, "TEST", "sell", sell_date, qty="100", price="15")

    async with Session() as session:
        await recompute_holding(session, "TEST")
        await session.commit()

    async with Session() as session:
        h = await _read_holding(session, HoldingRecord, "TEST")
        assert _approx(h.quantity, "0"), f"quantity={h.quantity}"
        assert _approx(h.cost_price, "0"), f"cost_price={h.cost_price}"
        assert _approx(h.total_invested, "0"), f"total_invested={h.total_invested}"
        assert h.liquidated_at == sell_date, f"liquidated_at={h.liquidated_at} expected={sell_date}"
    print(f"    ✅ q=0 cost=0 total=0 liquidated_at={h.liquidated_at}")
    await engine.dispose()


# ════════════════════════════════════════════════════
# 测试 6：archive_holding — 清仓后整体搬到 closed_holdings
# ════════════════════════════════════════════════════
async def test_archive_on_full_sell():
    print("\n[6/8] 100@10 → sell 100@15 → recompute → archive → closed_holdings 出现一行")
    engine, HoldingRecord, TxnRecord = await _make_engine()
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    import app.core.database as db_mod
    db_mod.async_session = Session
    from app.services.asset_holding_service import recompute_holding, archive_holding
    from app.models.orm.closed_holding_orm import ClosedHoldingRecord, ClosedTransactionRecord
    from sqlalchemy import select

    initial_date = date(2024, 1, 1)
    sell_date = date(2024, 6, 1)
    async with Session() as session:
        await _seed_holding(session, HoldingRecord, "TEST", "100", "10", "1000", dt=initial_date)
        await _add_txn(session, TxnRecord, "TEST", "sell", sell_date, qty="100", price="15")

    async with Session() as session:
        await recompute_holding(session, "TEST")
        closed_id = await archive_holding(session, "TEST")
        await session.commit()
        assert closed_id is not None and closed_id > 0

    # 验证：原表已清空，归档表有数据
    async with Session() as session:
        # asset_holdings 应该没有 TEST 了
        h = (await session.execute(
            select(HoldingRecord).where(HoldingRecord.ticker == "TEST")
        )).scalar_one_or_none()
        assert h is None, f"asset_holdings 应该没有 TEST，实际：{h}"

        # closed_holdings 应该有一行
        ch = (await session.execute(
            select(ClosedHoldingRecord).where(ClosedHoldingRecord.id == closed_id)
        )).scalar_one()
        # realized_pnl = sum_sell - sum_buy - initial_total = 1500 - 0 - 1000 = 500
        assert _approx(ch.realized_pnl, "500"), f"realized_pnl={ch.realized_pnl}"
        assert ch.closed_at == sell_date, f"closed_at={ch.closed_at}"
        # holding_days = (sell_date - initial_date) + 1 = 152 + 1 = 153
        expected_days = (sell_date - initial_date).days + 1
        assert ch.holding_days == expected_days, f"holding_days={ch.holding_days} expected={expected_days}"

        # closed_transactions 应该有一笔 sell
        cts = (await session.execute(
            select(ClosedTransactionRecord).where(ClosedTransactionRecord.closed_holding_id == closed_id)
        )).scalars().all()
        assert len(cts) == 1, f"expected 1 closed_transaction, got {len(cts)}"
        assert cts[0].type == "sell"
        assert _approx(cts[0].quantity, "100")

        # 原 transactions 表应该被清空
        ts = (await session.execute(
            select(TxnRecord).where(TxnRecord.ticker == "TEST")
        )).scalars().all()
        assert len(ts) == 0, f"原 transactions 表 TEST 应该已删，实际剩 {len(ts)} 条"

    print(f"    ✅ archive_id={closed_id} realized_pnl=500 holding_days={expected_days} 原表已清空")
    await engine.dispose()


# ════════════════════════════════════════════════════
# 测试 7：从未清仓 → liquidated_at 始终 None + first_buy_date 不变
# ════════════════════════════════════════════════════
async def test_no_liquidation_keeps_first_buy_date():
    print("\n[7/8] 100@10 + buy 50@12 (持续持仓) → first_buy_date 保持初始值")
    engine, HoldingRecord, TxnRecord = await _make_engine()
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    import app.core.database as db_mod
    db_mod.async_session = Session
    from app.services.asset_holding_service import recompute_holding

    initial_date = date(2024, 1, 1)
    async with Session() as session:
        await _seed_holding(session, HoldingRecord, "TEST", "100", "10", "1000", dt=initial_date)
        await _add_txn(session, TxnRecord, "TEST", "buy", date(2024, 3, 1),
                        qty="50", price="12", amount="600")

    async with Session() as session:
        await recompute_holding(session, "TEST")
        await session.commit()

    async with Session() as session:
        h = await _read_holding(session, HoldingRecord, "TEST")
        assert h.liquidated_at is None
        assert h.first_buy_date == initial_date, f"first_buy_date={h.first_buy_date} expected={initial_date}"
    print(f"    ✅ liquidated_at=None first_buy_date={h.first_buy_date}（保持建仓日期）")
    await engine.dispose()


# ════════════════════════════════════════════════════
# 测试 8：做 T 赚到比总投入还多 → cost_price/total_invested 钉死 0（白拿股票上限）
# ════════════════════════════════════════════════════
async def test_cost_floor_zero():
    print("\n[8/8] 100@10 (t=1000) → 卖 50@30 → t 钉死 0, cost=0（白拿股票）")
    engine, HoldingRecord, TxnRecord = await _make_engine()
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    import app.core.database as db_mod
    db_mod.async_session = Session
    from app.services.asset_holding_service import recompute_holding

    async with Session() as session:
        await _seed_holding(session, HoldingRecord, "TEST", "100", "10", "1000")
        await _add_txn(session, TxnRecord, "TEST", "sell", date(2024, 2, 1),
                        qty="50", price="30")

    async with Session() as session:
        await recompute_holding(session, "TEST")
        await session.commit()

    async with Session() as session:
        h = await _read_holding(session, HoldingRecord, "TEST")
        # 卖 50@30：t = 1000 - 30×50 = -500 → 钉死 0
        # 剩 50 股，t=0 → cost_price = 0/50 = 0
        assert _approx(h.quantity, "50"), f"quantity={h.quantity}"
        assert _approx(h.total_invested, "0"), f"total_invested={h.total_invested}"
        assert _approx(h.cost_price, "0"), f"cost_price={h.cost_price}"
    print(f"    ✅ q={h.quantity} cost={h.cost_price} total={h.total_invested}（白拿）")
    await engine.dispose()


async def main():
    print("=" * 60)
    print("recompute_holding 单元测试")
    print("=" * 60)
    await test_baseline_only()
    await test_buy_after_baseline()
    await test_sell_lowers_cost()
    await test_oversell_raises()
    await test_full_liquidation()
    await test_archive_on_full_sell()
    await test_no_liquidation_keeps_first_buy_date()
    await test_cost_floor_zero()
    print("\n" + "=" * 60)
    print("✅ 全部 8 个测试通过")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
