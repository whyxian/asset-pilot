"""AssetHoldingService 单元测试 — 覆盖 CRUD + 级联删除 + list_holdings_with_quotes 三元组"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.exceptions import BusinessError
from app.models.asset_holding import AssetHoldingCreate, AssetHoldingUpdate
from app.models.asset_quote import AssetQuote
from test.conftest import approx


# ════════════════════════════════════════════════════
# create_holding
# ════════════════════════════════════════════════════

async def test_create_holding_writes_initial(Session, seed_variety, read_holding):
    """新建持仓 → initial_* 等于当前 quantity/cost_price/total_invested"""
    from app.services.asset_holding_service import AssetHoldingService

    await seed_variety(ticker="TEST")
    payload = AssetHoldingCreate(
        ticker="TEST", name="测试品种", market="CN", asset_class="STOCK",
        currency="CNY",
        quantity=Decimal("100"), cost_price=Decimal("10"), total_invested=Decimal("1000"),
        first_buy_date=date(2024, 1, 1),
    )
    await AssetHoldingService().create_holding(payload)

    h = await read_holding()
    assert approx(h.quantity, "100")
    assert approx(h.initial_quantity, "100")
    assert approx(h.initial_cost_price, "10")
    assert approx(h.initial_total_invested, "1000")


async def test_create_holding_unknown_variety_fails(Session):
    """品种目录里没有该 ticker → BusinessError"""
    from app.services.asset_holding_service import AssetHoldingService

    payload = AssetHoldingCreate(
        ticker="UNKNOWN", name="", market="CN", asset_class="STOCK",
        currency="CNY",
        quantity=Decimal("100"), cost_price=Decimal("10"), total_invested=Decimal("1000"),
        first_buy_date=date(2024, 1, 1),
    )
    with pytest.raises(BusinessError, match="未识别的品种"):
        await AssetHoldingService().create_holding(payload)


# ════════════════════════════════════════════════════
# update_holding
# ════════════════════════════════════════════════════

async def test_update_recomputes_when_baseline_changes(Session, seed_holding, read_holding):
    """改 quantity → 同步到 initial_*,触发重算"""
    from app.services.asset_holding_service import AssetHoldingService

    await seed_holding(qty="100", cost="10", total="1000")

    update = AssetHoldingUpdate(quantity=Decimal("200"), total_invested=Decimal("2000"))
    await AssetHoldingService().update_holding("TEST", "STOCK", "CN", update)

    h = await read_holding()
    # 没有交易,重算后派生 = baseline
    assert approx(h.quantity, "200")
    assert approx(h.initial_quantity, "200")
    assert approx(h.total_invested, "2000")
    assert approx(h.initial_total_invested, "2000")


async def test_update_no_recompute_for_meta_changes(Session, seed_holding, read_holding):
    """改 name → 不触发重算(只改元数据)"""
    from app.services.asset_holding_service import AssetHoldingService

    await seed_holding(qty="100", cost="10", total="1000")

    update = AssetHoldingUpdate(name="新名字")
    await AssetHoldingService().update_holding("TEST", "STOCK", "CN", update)

    h = await read_holding()
    assert h.name == "新名字"
    # quantity / cost_price 等不变
    assert approx(h.quantity, "100")


# ════════════════════════════════════════════════════
# delete_holding
# ════════════════════════════════════════════════════

async def test_delete_holding_cascades_transactions(Session, seed_holding, add_txn):
    """删除持仓 → 该品种全部交易也被删,返回交易条数"""
    from app.services.asset_holding_service import AssetHoldingService
    from app.models.orm.transaction_orm import TransactionRecord
    from app.models.orm.asset_holding_orm import AssetHoldingRecord

    await seed_holding(qty="100", cost="10", total="1000")
    await add_txn("TEST", "buy", date(2024, 6, 1), qty="50", price="12", amount="600")
    await add_txn("TEST", "sell", date(2024, 6, 2), qty="20", price="15")

    txn_count = await AssetHoldingService().delete_holding("TEST", "STOCK", "CN")
    assert txn_count == 2

    # 持仓 + 交易都没了
    async with Session() as s:
        h = (await s.execute(
            select(AssetHoldingRecord).where(AssetHoldingRecord.ticker == "TEST")
        )).scalar_one_or_none()
        assert h is None
        ts = (await s.execute(
            select(TransactionRecord).where(TransactionRecord.ticker == "TEST")
        )).scalars().all()
        assert len(ts) == 0


async def test_delete_holding_not_found_returns_minus_one(Session):
    """删除不存在的持仓 → 返回 -1"""
    from app.services.asset_holding_service import AssetHoldingService

    result = await AssetHoldingService().delete_holding("UNKNOWN", "STOCK", "CN")
    assert result == -1


# ════════════════════════════════════════════════════
# list_holdings_with_quotes
# ════════════════════════════════════════════════════

async def test_list_holdings_with_quotes_uses_triple_key(Session, seed_holding, monkeypatch):
    """同 ticker 不同品种(STOCK+CN+000001 vs FUND+CN+000001)行情按三元组分发,不串扰"""
    from app.services.asset_holding_service import AssetHoldingService

    # 建两条同 ticker 不同品种的持仓
    await seed_holding(ticker="000001", asset_class="STOCK", market="CN",
                       qty="100", cost="10", total="1000")
    await seed_holding(ticker="000001", asset_class="FUND", market="CN",
                       qty="100", cost="2", total="200", ensure_variety=True)

    # mock 行情:STOCK 返回 11.5, FUND 返回 2.5
    async def fake_fetch(asset_class, market, tickers, force_refresh=False):
        if asset_class == "STOCK":
            return [AssetQuote(
                ticker="000001", asset_class="STOCK", market="CN",
                name="平安银行", price=Decimal("11.5"), currency="CNY",
            )]
        if asset_class == "FUND":
            return [AssetQuote(
                ticker="000001", asset_class="FUND", market="CN",
                name="华夏成长", price=Decimal("2.5"), currency="CNY",
            )]
        return []

    svc = AssetHoldingService()
    monkeypatch.setattr(svc._quote_svc, "fetch_quotes_by_asset_class", fake_fetch)

    # mock 汇率（避免测试真连网），CNY=7
    from app.utils.exchange_rate import RatesSnapshot
    async def fake_fetch_rates():
        return RatesSnapshot(rates={"USD": 1.0, "CNY": 7.0}, source_date="2026-06-19", is_stale=False)
    monkeypatch.setattr("app.services.asset_holding_service.fetch_rates", fake_fetch_rates)

    result = await svc.list_holdings_with_quotes()
    assert len(result.holdings) == 2

    by_class = {r.asset_class: r for r in result.holdings}
    # STOCK 拿到 11.5,不被 FUND 的 2.5 串扰
    assert approx(by_class["STOCK"].current_price, "11.5")
    # FUND 拿到 2.5
    assert approx(by_class["FUND"].current_price, "2.5")


async def test_list_holdings_with_quotes_pnl_calculation(Session, seed_holding, monkeypatch):
    """验证 pnl / pnl_pct / annualized 计算"""
    from app.services.asset_holding_service import AssetHoldingService

    # 100 股 @10 投入 1000;现价 12 → market_value 1200, pnl 200, pnl_pct 20%
    await seed_holding(qty="100", cost="10", total="1000", dt=date(2024, 1, 1))

    async def fake_fetch(asset_class, market, tickers, force_refresh=False):
        return [AssetQuote(
            ticker="TEST", asset_class="STOCK", market="CN",
            name="测试", price=Decimal("12"), currency="CNY",
        )]

    svc = AssetHoldingService()
    monkeypatch.setattr(svc._quote_svc, "fetch_quotes_by_asset_class", fake_fetch)

    # mock 汇率（避免测试真连网），CNY=7
    from app.utils.exchange_rate import RatesSnapshot
    async def fake_fetch_rates():
        return RatesSnapshot(rates={"USD": 1.0, "CNY": 7.0}, source_date="2026-06-19", is_stale=False)
    monkeypatch.setattr("app.services.asset_holding_service.fetch_rates", fake_fetch_rates)

    result = await svc.list_holdings_with_quotes()
    assert len(result.holdings) == 1
    h = result.holdings[0]
    assert approx(h.current_price, "12")
    assert approx(h.market_value, "1200")
    assert approx(h.pnl, "200")
    assert h.pnl_pct is not None and abs(h.pnl_pct - 20.0) < 0.01

    # market_summary：单市场 CN，count=1，占比 100%
    assert len(result.market_summary) == 1
    assert result.market_summary[0].market == "CN"
    assert result.market_summary[0].count == 1
    assert result.market_summary[0].pct == 100.0
