"""OverviewService 单元测试 — 覆盖 _calc_annualized + get_overview 聚合逻辑

执行：
    .venv/bin/pytest test/test_overview_service.py -v
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.models.asset_holding import AssetHolding
from app.models.asset_quote import AssetQuote
from app.models.overview import OverviewStats
from app.services.overview_service import OverviewService


# ════════════════════════════════════════════════════
# _calc_annualized（纯静态方法，无需 mock）
# ════════════════════════════════════════════════════

def test_calc_annualized_normal():
    """2 年持有，成本 10 → 现价 11（10% 总回报），年化 ≈ 4.88%"""
    buy_date = date(2024, 1, 1)
    today = date(2025, 12, 31)
    result = OverviewService._calc_annualized(
        Decimal("11"), Decimal("10"), buy_date, today,
    )
    assert result is not None
    # holding_days = 730 + 1 = 731; annualized = 10 * 365/731 ≈ 4.9932
    assert abs(result - 4.99) < 0.1


def test_calc_annualized_cost_zero_with_price():
    """cost_price=0 + current_price>0 → 返回 "+∞%"（零成本持有）"""
    result = OverviewService._calc_annualized(
        Decimal("11"), Decimal("0"), date(2024, 1, 1), date(2025, 1, 1),
    )
    assert result == "+∞%"


def test_calc_annualized_cost_zero_no_price():
    """cost_price=0 + current_price=0 → 返回 None（无意义的零持仓）"""
    result = OverviewService._calc_annualized(
        Decimal("0"), Decimal("0"), date(2024, 1, 1), date(2025, 1, 1),
    )
    assert result is None


def test_calc_annualized_no_date():
    """first_buy_date=None → 返回 None"""
    result = OverviewService._calc_annualized(
        Decimal("11"), Decimal("10"), None, date(2025, 1, 1),
    )
    assert result is None


def test_calc_annualized_same_day():
    """today == first_buy_date → holding_days = 1（不是 0），仍然可算"""
    result = OverviewService._calc_annualized(
        Decimal("11"), Decimal("10"), date(2025, 1, 1), date(2025, 1, 1),
    )
    # holding_days = 0 + 1 = 1，total_return = 10%，annualized = 10 * 365/1 = 3650
    assert result is not None
    assert result == 3650.0


def test_calc_annualized_negative_return():
    """亏损也正确计算：成本 10，现价 8（-20% 总回报）"""
    buy_date = date(2024, 1, 1)
    today = date(2025, 1, 1)
    result = OverviewService._calc_annualized(
        Decimal("8"), Decimal("10"), buy_date, today,
    )
    assert result is not None
    # total_return_pct = (8-10)/10 * 100 = -20; holding_days = 366+1=367
    # annualized = -20 * 365/367 ≈ -19.89
    assert result < 0
    assert abs(result - (-19.89)) < 0.5


# ════════════════════════════════════════════════════
# get_overview
# ════════════════════════════════════════════════════

async def test_get_overview_empty():
    """无持仓 → 返回默认 OverviewStats（全零）"""
    svc = OverviewService()

    # mock holding_repo.list_holdings 返回空列表
    mock_repo = AsyncMock()
    mock_repo.list_holdings = AsyncMock(return_value=[])
    monkeypatch_repo = pytest.MonkeyPatch()
    monkeypatch_repo.setattr(svc, "_holding_repo", mock_repo)

    try:
        result = await svc.get_overview()
    finally:
        monkeypatch_repo.undo()

    assert isinstance(result, OverviewStats)
    assert result.total_value == Decimal("0")
    assert result.total_cost == Decimal("0")
    assert result.allocation == []


async def test_get_overview_with_holdings():
    """有持仓 → 验证总值/成本/盈亏/配比/年化计算"""
    svc = OverviewService()

    # 准备持仓数据
    h1 = AssetHolding(
        ticker="AAPL", name="Apple", market="US", asset_class="STOCK",
        currency="USD", quantity=Decimal("10"), cost_price=Decimal("150"),
        total_invested=Decimal("1500"), first_buy_date=date(2024, 1, 1),
    )
    h2 = AssetHolding(
        ticker="600519", name="贵州茅台", market="CN", asset_class="STOCK",
        currency="CNY", quantity=Decimal("5"), cost_price=Decimal("1800"),
        total_invested=Decimal("9000"), first_buy_date=date(2024, 6, 1),
    )

    # mock repo
    mock_repo = AsyncMock()
    mock_repo.list_holdings = AsyncMock(return_value=[h1, h2])

    # mock quote service
    mock_quote_svc = AsyncMock()
    async def fake_fetch(asset_class, market, tickers, force_refresh=False):
        if asset_class == "STOCK" and market == "US":
            return [AssetQuote(
                ticker="AAPL", asset_class="STOCK", market="US",
                name="Apple", price=Decimal("170"), currency="USD",
            )]
        if asset_class == "STOCK" and market == "CN":
            return [AssetQuote(
                ticker="600519", asset_class="STOCK", market="CN",
                name="贵州茅台", price=Decimal("1900"), currency="CNY",
            )]
        return []
    mock_quote_svc.fetch_quotes_by_asset_class = fake_fetch

    # mock 汇率：USD 为基准，CNY=7（convert_with_rates 是纯同步函数，走真实实现）
    async def fake_fetch_rates():
        return {"USD": Decimal("1"), "CNY": Decimal("7")}

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_holding_repo", mock_repo)
    mp.setattr(svc, "_quote_svc", mock_quote_svc)
    mp.setattr("app.services.overview_service.fetch_rates", fake_fetch_rates)

    try:
        result = await svc.get_overview()
    finally:
        mp.undo()

    # AAPL: mv=10×170=1700 USD → 1700×7=11900 CNY, cost=1500×7=10500 CNY
    # 600519: mv=5×1900=9500 CNY, cost=9000 CNY
    # total_value = 11900 + 9500 = 21400
    # total_cost  = 10500 + 9000 = 19500
    assert abs(result.total_value - Decimal("21400")) < Decimal("1")
    assert abs(result.total_cost - Decimal("19500")) < Decimal("1")
    assert abs(result.total_pnl - Decimal("1900")) < Decimal("1")
    assert result.total_pnl_pct is not None
    assert abs(result.total_pnl_pct - 9.74) < 0.5

    # 配比：US=11900, CN=9500
    assert len(result.allocation) == 2
    assert result.allocation[0].market == "US"  # 市值大排前面
    assert result.allocation[1].market == "CN"

    # 年化应为非 None（两只持仓都有行情和日期）
    assert result.annualized_return is not None


# ════════════════════════════════════════════════════
# _fetch_quote_map — 并发拉取 + 超时熔断 + 单组容错
# ════════════════════════════════════════════════════

async def test_fetch_quote_map_timeout_drops_slow_group():
    """某组超时未返回 → 丢弃该组，保留已完成的组行情"""
    import asyncio
    svc = OverviewService()

    async def fake_fetch(ac, market, tickers, force_refresh=False):
        if market == "US":
            return [AssetQuote(
                ticker="AAPL", asset_class="STOCK", market="US",
                name="Apple", price=Decimal("170"), currency="USD",
            )]
        # 慢组：模拟数据源抽风
        await asyncio.sleep(0.5)
        return [AssetQuote(
            ticker="000001", asset_class="FUND", market="CN",
            name="华夏成长", price=Decimal("1.2"), currency="CNY",
        )]

    mp = pytest.MonkeyPatch()
    mp.setattr(svc._quote_svc, "fetch_quotes_by_asset_class", fake_fetch)
    # 把超时压到极小，让慢组必被丢弃
    mp.setattr("app.services.overview_service._QUOTE_FETCH_TIMEOUT", 0.1)
    try:
        groups = {("STOCK", "US"): ["AAPL"], ("FUND", "CN"): ["000001"]}
        quote_map = await svc._fetch_quote_map(groups, force_refresh=False)
    finally:
        mp.undo()

    # 快组行情保留，慢组被丢弃
    assert "AAPL" in quote_map
    assert "000001" not in quote_map


async def test_fetch_quote_map_swallows_group_exception():
    """某组抛异常 → 不影响其他组，返回已成功组的行情"""
    svc = OverviewService()

    async def fake_fetch(ac, market, tickers, force_refresh=False):
        if market == "US":
            return [AssetQuote(
                ticker="AAPL", asset_class="STOCK", market="US",
                name="Apple", price=Decimal("170"), currency="USD",
            )]
        raise RuntimeError("coinglass down")

    mp = pytest.MonkeyPatch()
    mp.setattr(svc._quote_svc, "fetch_quotes_by_asset_class", fake_fetch)
    try:
        groups = {("STOCK", "US"): ["AAPL"], ("CRYPTO", "CRYPTO"): ["BTC"]}
        quote_map = await svc._fetch_quote_map(groups, force_refresh=False)
    finally:
        mp.undo()

    # 异常组被吞掉，正常组行情保留
    assert "AAPL" in quote_map
    assert "BTC" not in quote_map
