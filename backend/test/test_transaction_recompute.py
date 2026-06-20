"""recompute_holding / archive_holding 单元测试

绕过 HTTP,直接调用 service 层函数,用内存 SQLite 验证算法正确性。
fixture 见 conftest.py。

执行：
    .venv/bin/pytest test/test_transaction_recompute.py -v
"""

from datetime import date

import pytest

from app.core.exceptions import BusinessError
from test.conftest import approx


# ════════════════════════════════════════════════════
# 测试 1：仅基线，无交易 → 派生字段 = 基线
# ════════════════════════════════════════════════════
async def test_baseline_only(Session, seed_holding, read_holding):
    from app.services.asset_holding_service import recompute_holding

    await seed_holding(ticker="TEST", qty="100", cost="10", total="1000")

    async with Session() as session:
        await recompute_holding(session, "TEST", "STOCK", "CN")
        await session.commit()

    h = await read_holding("TEST")
    assert approx(h.quantity, "100")
    assert approx(h.cost_price, "10")
    assert approx(h.total_invested, "1000")


# ════════════════════════════════════════════════════
# 测试 2：基线 + 一笔买入 → 加权平均
# ════════════════════════════════════════════════════
async def test_buy_after_baseline(Session, seed_holding, add_txn, read_holding):
    from app.services.asset_holding_service import recompute_holding

    await seed_holding(qty="100", cost="10", total="1000")
    await add_txn("TEST", "buy", date(2024, 2, 1), qty="50", price="12", amount="600")

    async with Session() as session:
        await recompute_holding(session, "TEST", "STOCK", "CN")
        await session.commit()

    h = await read_holding()
    # 基线 100@10 (t=1000) + buy 50@12 (amt=600) → q=150 t=1600 p≈10.667
    assert approx(h.quantity, "150")
    assert approx(h.total_invested, "1600")
    assert approx(h.cost_price, "10.667")


# ════════════════════════════════════════════════════
# 测试 3：买入后卖出 — 降低成本法
# ════════════════════════════════════════════════════
async def test_sell_lowers_cost(Session, seed_holding, add_txn, read_holding):
    from app.services.asset_holding_service import recompute_holding

    await seed_holding(qty="100", cost="10", total="1000")
    await add_txn("TEST", "buy", date(2024, 2, 1), qty="50", price="12", amount="600")
    await add_txn("TEST", "sell", date(2024, 3, 1), qty="30", price="15")

    async with Session() as session:
        await recompute_holding(session, "TEST", "STOCK", "CN")
        await session.commit()

    h = await read_holding()
    # 买完后 q=150 t=1600 p≈10.667
    # 卖 30@15: t = 1600 - 15×30 = 1150; p = 1150/120 ≈ 9.583
    assert approx(h.quantity, "120")
    assert approx(h.total_invested, "1150")
    assert approx(h.cost_price, "9.583")


# ════════════════════════════════════════════════════
# 测试 4：卖超 → BusinessError
# ════════════════════════════════════════════════════
async def test_oversell_raises(Session, seed_holding, add_txn):
    from app.services.asset_holding_service import recompute_holding

    await seed_holding(qty="100", cost="10", total="1000")
    await add_txn("TEST", "sell", date(2024, 2, 1), qty="200", price="12")

    async with Session() as session:
        with pytest.raises(BusinessError, match="卖出"):
            await recompute_holding(session, "TEST", "STOCK", "CN")


# ════════════════════════════════════════════════════
# 测试 5：清仓 → q=0, cost=0, total=0, liquidated_at=最后一笔 sell 日期
# ════════════════════════════════════════════════════
async def test_full_liquidation(Session, seed_holding, add_txn, read_holding):
    from app.services.asset_holding_service import recompute_holding

    sell_date = date(2024, 2, 1)
    await seed_holding(qty="100", cost="10", total="1000")
    await add_txn("TEST", "sell", sell_date, qty="100", price="15")

    async with Session() as session:
        await recompute_holding(session, "TEST", "STOCK", "CN")
        await session.commit()

    h = await read_holding()
    assert approx(h.quantity, "0")
    assert approx(h.cost_price, "0")
    assert approx(h.total_invested, "0")
    assert h.liquidated_at == sell_date


# ════════════════════════════════════════════════════
# 测试 6：archive_holding 把清仓持仓搬到 closed_*,原表清空
# ════════════════════════════════════════════════════
async def test_archive_on_full_sell(Session, seed_holding, add_txn):
    from sqlalchemy import select
    from app.services.asset_holding_service import recompute_holding, archive_holding
    from app.models.orm.asset_holding_orm import AssetHoldingRecord
    from app.models.orm.transaction_orm import TransactionRecord
    from app.models.orm.closed_holding_orm import ClosedHoldingRecord, ClosedTransactionRecord

    initial_date = date(2024, 1, 1)
    sell_date = date(2024, 6, 1)
    await seed_holding(qty="100", cost="10", total="1000", dt=initial_date)
    await add_txn("TEST", "sell", sell_date, qty="100", price="15")

    async with Session() as session:
        await recompute_holding(session, "TEST", "STOCK", "CN")
        closed_id = await archive_holding(session, "TEST", "STOCK", "CN")
        await session.commit()
        assert closed_id is not None and closed_id > 0

    async with Session() as session:
        # 原表无 TEST
        h = (await session.execute(
            select(AssetHoldingRecord).where(AssetHoldingRecord.ticker == "TEST")
        )).scalar_one_or_none()
        assert h is None
        ts = (await session.execute(
            select(TransactionRecord).where(TransactionRecord.ticker == "TEST")
        )).scalars().all()
        assert len(ts) == 0

        # 归档表有数据
        ch = (await session.execute(
            select(ClosedHoldingRecord).where(ClosedHoldingRecord.id == closed_id)
        )).scalar_one()
        # realized_pnl = sum_sell - sum_buy = 1500 - 1000 = 500（建仓buy 1000 + sell 1500）
        assert approx(ch.realized_pnl, "500")
        assert ch.closed_at == sell_date
        expected_days = (sell_date - initial_date).days + 1
        assert ch.holding_days == expected_days

        cts = (await session.execute(
            select(ClosedTransactionRecord).where(
                ClosedTransactionRecord.closed_holding_id == closed_id
            )
        )).scalars().all()
        # 建仓 buy + sell = 2 条归档交易
        assert len(cts) == 2
        types = {ct.type for ct in cts}
        assert types == {"buy", "sell"}


# ════════════════════════════════════════════════════
# 测试 7：从未清仓 → liquidated_at=None, first_buy_date 不变
# ════════════════════════════════════════════════════
async def test_no_liquidation_keeps_first_buy_date(Session, seed_holding, add_txn, read_holding):
    from app.services.asset_holding_service import recompute_holding

    initial_date = date(2024, 1, 1)
    await seed_holding(qty="100", cost="10", total="1000", dt=initial_date)
    await add_txn("TEST", "buy", date(2024, 3, 1), qty="50", price="12", amount="600")

    async with Session() as session:
        await recompute_holding(session, "TEST", "STOCK", "CN")
        await session.commit()

    h = await read_holding()
    assert h.liquidated_at is None
    assert h.first_buy_date == initial_date


# ════════════════════════════════════════════════════
# 测试 8：做 T 赚到比总投入还多 → t 钉死 0,cost=0(白拿股票)
# ════════════════════════════════════════════════════
async def test_cost_floor_zero(Session, seed_holding, add_txn, read_holding):
    from app.services.asset_holding_service import recompute_holding

    await seed_holding(qty="100", cost="10", total="1000")
    await add_txn("TEST", "sell", date(2024, 2, 1), qty="50", price="30")

    async with Session() as session:
        await recompute_holding(session, "TEST", "STOCK", "CN")
        await session.commit()

    h = await read_holding()
    # 卖 50@30: t = 1000 - 30×50 = -500 → 钉死 0
    # 剩 50 股,t=0 → cost=0
    assert approx(h.quantity, "50")
    assert approx(h.total_invested, "0")
    assert approx(h.cost_price, "0")
