"""OverviewService 单元测试 — 覆盖 get_overview 聚合逻辑

执行：
    .venv/bin/pytest test/test_overview_service.py -v
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.models.asset_holding import AssetHolding
from app.models.asset_quote import AssetQuote, QuoteStatus
from app.models.overview import OverviewStats
from app.services.overview_service import OverviewService


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

    # mock quote service：直接返回并发拉取后的 quote_map（三元组 key → (行情, 状态)）
    mock_quote_svc = AsyncMock()
    async def fake_fetch_quote_map(groups, force_refresh=False, timeout=None):
        return {
            ("STOCK", "US", "AAPL"): (AssetQuote(
                ticker="AAPL", asset_class="STOCK", market="US",
                name="Apple", price=Decimal("170"), currency="USD",
            ), QuoteStatus.REALTIME),
            ("STOCK", "CN", "600519"): (AssetQuote(
                ticker="600519", asset_class="STOCK", market="CN",
                name="贵州茅台", price=Decimal("1900"), currency="CNY",
            ), QuoteStatus.REALTIME),
        }
    mock_quote_svc.fetch_quote_map_concurrent = fake_fetch_quote_map

    # mock 汇率：USD 为基准，CNY=7（convert_with_rates 是纯同步函数，走真实实现）
    async def fake_fetch_rates():
        from app.utils.exchange_rate import RatesSnapshot
        return RatesSnapshot(
            rates={"USD": Decimal("1"), "CNY": Decimal("7")},
            source_date="2026-06-19",
            is_stale=False,
        )

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_holding_repo", mock_repo)
    mp.setattr(svc, "_quote_svc", mock_quote_svc)
    mp.setattr("app.services.overview_service.fetch_rates", fake_fetch_rates)
    # mock ClosedHoldingRepository（概览已追加已归档盈亏，测试无归档数据）
    from app.repositories.closed_holding_repository import ClosedHoldingRepository
    mp.setattr(ClosedHoldingRepository, "list_closed_holdings", AsyncMock(return_value=[]))

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

    # 历史累计收益（Modified Dietz）
    assert result.cumulative_return_pct is not None
    assert isinstance(result.cumulative_return_pct, float)

    # 汇率元数据透传
    assert result.rate_source_date == "2026-06-19"
    assert result.rate_stale is False
