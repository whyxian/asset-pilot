"""SnapshotService 单元测试 — 覆盖快照写入 + 查询 + 历史汇率换算

执行：
    .venv/bin/pytest test/test_snapshot_service.py -v
"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models.asset_holding import AssetHolding
from app.models.asset_quote import AssetQuote, QuoteStatus
from app.models.orm.networth_snapshot_orm import NetWorthSnapshotRecord
from app.services.snapshot_service import SnapshotService
from test.conftest import approx


# ════════════════════════════════════════════════════
# take_snapshot
# ════════════════════════════════════════════════════

async def _setup_snapshot_mocks(svc: SnapshotService, mp: pytest.MonkeyPatch,
                                 holdings: list[AssetHolding],
                                 quotes_map: dict):
    """统一设置 mock：holding_repo / quote_svc / fetch_rates_snapshot"""
    mock_repo = AsyncMock()
    mock_repo.list_holdings = AsyncMock(return_value=holdings)

    # mock fetch_quote_map_concurrent：把 quotes_map 按 (ac, market) 分组转成三元组 key dict
    async def fake_fetch_quote_map(groups, force_refresh=False, timeout=None):
        quote_map = {}
        for (ac, market), _tickers in groups.items():
            for q in quotes_map.get((ac, market), []):
                quote_map[(ac, market, q.ticker)] = (q, QuoteStatus.REALTIME)
        return quote_map

    mock_quote_svc = AsyncMock()
    mock_quote_svc.fetch_quote_map_concurrent = fake_fetch_quote_map

    fake_rates = {"USD": 1.0, "CNY": 7.2, "HKD": 7.8, "EUR": 0.92}

    async def fake_fetch_rates():
        return fake_rates

    mp.setattr(svc, "_holding_repo", mock_repo)
    mp.setattr(svc, "_quote_svc", mock_quote_svc)
    mp.setattr("app.services.snapshot_service.fetch_rates_snapshot", fake_fetch_rates)
    return fake_rates


async def test_take_snapshot_writes_both_tables(Session, seed_holding, seed_variety):
    """take_snapshot 单事务写入 networth + asset 两张表"""
    from app.models.orm.asset_snapshot_orm import AssetSnapshotRecord

    svc = SnapshotService()
    mp = pytest.MonkeyPatch()

    h = AssetHolding(
        ticker="AAPL", name="Apple", market="US", asset_class="STOCK",
        currency="USD", quantity=Decimal("10"), cost_price=Decimal("150"),
        total_invested=Decimal("1500"), first_buy_date=date(2024, 1, 1),
    )
    quotes_map = {
        ("STOCK", "US"): [AssetQuote(
            ticker="AAPL", asset_class="STOCK", market="US",
            name="Apple", price=Decimal("170"), currency="USD",
        )],
    }
    await _setup_snapshot_mocks(svc, mp, [h], quotes_map)

    try:
        result = await svc.take_snapshot(snapshot_date=date(2026, 6, 15))
    finally:
        mp.undo()

    # 验证返回值
    assert result.snapshot_date == date(2026, 6, 15)
    assert result.currency == "USD"
    assert approx(result.total_value, "1700")  # 10 * 170
    assert approx(result.total_cost, "1500")
    assert approx(result.total_pnl, "200")

    # 验证 DB 两张表都被写入
    async with Session() as s:
        nw = (await s.execute(select(NetWorthSnapshotRecord))).scalars().all()
        assert len(nw) == 1
        assert nw[0].snapshot_date == date(2026, 6, 15)
        assert approx(nw[0].total_value_usd, "1700")
        # fx_rates 被冻结
        rates = json.loads(nw[0].fx_rates)
        assert rates["CNY"] == 7.2

        assets = (await s.execute(select(AssetSnapshotRecord))).scalars().all()
        assert len(assets) == 1
        assert assets[0].ticker == "AAPL"
        assert approx(assets[0].market_value, "1700")
        assert approx(assets[0].market_value_usd, "1700")  # USD 直接相等


async def test_take_snapshot_multi_currency(Session, seed_variety):
    """多币种持仓：USD + CNY → USD 聚合 + 原币保留"""
    from app.models.orm.asset_snapshot_orm import AssetSnapshotRecord
    from app.models.orm.asset_holding_orm import AssetHoldingRecord

    # 用真实 DB 准备持仓（service 直接调用 holding_repo.list_holdings）
    await seed_variety(ticker="AAPL", asset_class="STOCK", market="US")
    await seed_variety(ticker="600519", asset_class="STOCK", market="CN")

    async with Session() as s:
        s.add(AssetHoldingRecord(
            ticker="AAPL", name="Apple", market="US", asset_class="STOCK", currency="USD",
            quantity=Decimal("10"), cost_price=Decimal("150"),
            total_invested=Decimal("1500"),
            initial_quantity=Decimal("10"), initial_cost_price=Decimal("150"),
            initial_total_invested=Decimal("1500"),
            first_buy_date=date(2024, 1, 1),
        ))
        s.add(AssetHoldingRecord(
            ticker="600519", name="贵州茅台", market="CN", asset_class="STOCK", currency="CNY",
            quantity=Decimal("5"), cost_price=Decimal("1800"),
            total_invested=Decimal("9000"),
            initial_quantity=Decimal("5"), initial_cost_price=Decimal("1800"),
            initial_total_invested=Decimal("9000"),
            first_buy_date=date(2024, 6, 1),
        ))
        await s.commit()

    svc = SnapshotService()
    mp = pytest.MonkeyPatch()

    quotes_map = {
        ("STOCK", "US"): [AssetQuote(
            ticker="AAPL", asset_class="STOCK", market="US",
            name="Apple", price=Decimal("170"), currency="USD",
        )],
        ("STOCK", "CN"): [AssetQuote(
            ticker="600519", asset_class="STOCK", market="CN",
            name="贵州茅台", price=Decimal("1900"), currency="CNY",
        )],
    }
    # 不能用 mock holding_repo,要让 service 读真实 DB
    fake_rates = {"USD": 1.0, "CNY": 7.2}

    async def fake_fetch_rates():
        return fake_rates

    async def fake_fetch_quote_map(groups, force_refresh=False, timeout=None):
        quote_map = {}
        for (ac, market), _tickers in groups.items():
            for q in quotes_map.get((ac, market), []):
                quote_map[(ac, market, q.ticker)] = (q, QuoteStatus.REALTIME)
        return quote_map

    mp.setattr(svc._quote_svc, "fetch_quote_map_concurrent", fake_fetch_quote_map)
    mp.setattr("app.services.snapshot_service.fetch_rates_snapshot", fake_fetch_rates)

    try:
        await svc.take_snapshot(snapshot_date=date(2026, 6, 15))
    finally:
        mp.undo()

    # 验证 USD 聚合：AAPL 1700 USD + 600519 9500 CNY / 7.2 ≈ 1319.44 USD ≈ 3019.44
    async with Session() as s:
        nw = (await s.execute(select(NetWorthSnapshotRecord))).scalar_one()
        assert approx(nw.total_value_usd, "3019.44", tol="0.5")

        # 品种快照同时存原币和 USD
        assets = (await s.execute(
            select(AssetSnapshotRecord).order_by(AssetSnapshotRecord.ticker)
        )).scalars().all()
        assert len(assets) == 2

        # 600519: 原币 9500 CNY, USD 9500/7.2 ≈ 1319.44
        moutai = next(a for a in assets if a.ticker == "600519")
        assert approx(moutai.market_value, "9500")
        assert approx(moutai.market_value_usd, "1319.44", tol="0.5")
        assert moutai.currency == "CNY"


async def test_take_snapshot_idempotent_same_day(Session, seed_holding):
    """当日重复触发 → INSERT OR REPLACE，覆盖旧值，不会报 UNIQUE 冲突"""
    from app.models.orm.asset_snapshot_orm import AssetSnapshotRecord

    await seed_holding(qty="100", cost="10", total="1000")

    svc = SnapshotService()
    mp = pytest.MonkeyPatch()

    quotes_map = {
        ("STOCK", "CN"): [AssetQuote(
            ticker="TEST", asset_class="STOCK", market="CN",
            name="测试", price=Decimal("12"), currency="CNY",
        )],
    }
    fake_rates = {"USD": 1.0, "CNY": 7.2}

    async def fake_fetch_rates():
        return fake_rates

    async def fake_fetch_quote_map(groups, force_refresh=False, timeout=None):
        # 每次 take_snapshot 调用时实时读 quotes_map，反映 price 的动态修改
        quote_map = {}
        for (ac, market), _tickers in groups.items():
            for q in quotes_map.get((ac, market), []):
                quote_map[(ac, market, q.ticker)] = (q, QuoteStatus.REALTIME)
        return quote_map

    mp.setattr(svc._quote_svc, "fetch_quote_map_concurrent", fake_fetch_quote_map)
    mp.setattr("app.services.snapshot_service.fetch_rates_snapshot", fake_fetch_rates)

    try:
        # 第一次：现价 12
        await svc.take_snapshot(snapshot_date=date(2026, 6, 15))

        # 改现价为 14 → 第二次快照同一天
        quotes_map[("STOCK", "CN")][0].price = Decimal("14")
        await svc.take_snapshot(snapshot_date=date(2026, 6, 15))
    finally:
        mp.undo()

    # 验证：依然只有 1 条 networth 和 1 条 asset，且值是最新（14）
    async with Session() as s:
        nw = (await s.execute(select(NetWorthSnapshotRecord))).scalars().all()
        assert len(nw) == 1
        assets = (await s.execute(select(AssetSnapshotRecord))).scalars().all()
        assert len(assets) == 1
        assert approx(assets[0].unit_value, "14")
        assert approx(assets[0].market_value, "1400")  # 100 * 14


# ════════════════════════════════════════════════════
# list_snapshots — 用快照里冻结的 fx_rates 换算
# ════════════════════════════════════════════════════

async def test_list_snapshots_uses_frozen_fx(Session):
    """历史快照查询用快照里的 fx_rates 换算（不用当前汇率）"""
    # 直接插入两条快照：一条用 fx=7.0（旧），一条用 fx=7.5（新）
    async with Session() as s:
        s.add(NetWorthSnapshotRecord(
            snapshot_date=date(2026, 6, 1),
            total_value_usd=Decimal("1000"),
            total_cost_usd=Decimal("800"),
            total_pnl_usd=Decimal("200"),
            total_pnl_pct=Decimal("25"),
            allocation="[]",
            fx_rates=json.dumps({"USD": 1.0, "CNY": 7.0}),
        ))
        s.add(NetWorthSnapshotRecord(
            snapshot_date=date(2026, 6, 15),
            total_value_usd=Decimal("1100"),
            total_cost_usd=Decimal("800"),
            total_pnl_usd=Decimal("300"),
            total_pnl_pct=Decimal("37.5"),
            allocation="[]",
            fx_rates=json.dumps({"USD": 1.0, "CNY": 7.5}),
        ))
        await s.commit()

    svc = SnapshotService()
    results = await svc.list_snapshots(currency="CNY")

    assert len(results) == 2
    # 升序：第一条 6/1
    assert results[0].snapshot_date == date(2026, 6, 1)
    assert approx(results[0].total_value, "7000")  # 1000 * 7.0（用快照里的旧汇率）

    # 第二条 6/15 用新汇率 7.5
    assert results[1].snapshot_date == date(2026, 6, 15)
    assert approx(results[1].total_value, "8250")  # 1100 * 7.5


async def test_list_snapshots_currency_usd(Session):
    """currency=USD 时直接返回 USD 值，不换算"""
    async with Session() as s:
        s.add(NetWorthSnapshotRecord(
            snapshot_date=date(2026, 6, 15),
            total_value_usd=Decimal("1000"),
            total_cost_usd=Decimal("800"),
            total_pnl_usd=Decimal("200"),
            total_pnl_pct=Decimal("25"),
            allocation="[]",
            fx_rates=json.dumps({"USD": 1.0, "CNY": 7.2}),
        ))
        await s.commit()

    svc = SnapshotService()
    results = await svc.list_snapshots(currency="USD")
    assert len(results) == 1
    assert approx(results[0].total_value, "1000")
    assert results[0].currency == "USD"


async def test_list_snapshots_empty(Session):
    """无快照 → 空列表"""
    svc = SnapshotService()
    results = await svc.list_snapshots(currency="CNY")
    assert results == []
