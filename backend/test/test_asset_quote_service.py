"""AssetQuoteService 单元测试 — 覆盖基金缓存策略 + 名称补全 + 路由分发

执行：
    .venv/bin/pytest test/test_asset_quote_service.py -v
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.asset_quote import AssetQuote
from app.services.asset_quote_service import AssetQuoteService


def _make_quote(ticker: str, price: str = "10", **kw) -> AssetQuote:
    """构造 AssetQuote 测试数据"""
    defaults = dict(
        ticker=ticker, asset_class="", market="CN", name=ticker,
        price=Decimal(price), currency="CNY", source="TEST",
    )
    defaults.update(kw)
    return AssetQuote(**defaults)


# ════════════════════════════════════════════════════
# fetch_fund_quotes — 缓存优先策略
# ════════════════════════════════════════════════════

async def test_fetch_fund_quotes_all_cached():
    """全部命中 15 分钟缓存 → 不调网络，返回缓存数据"""
    svc = AssetQuoteService()
    cached_quote = _make_quote("000001", asset_class="FUND", price="1.5")

    mock_fund_repo = AsyncMock()
    mock_fund_repo.get_recent_quotes = AsyncMock(
        return_value={"000001": cached_quote},
    )
    mock_fund_repo.fetch_realtime_quote = AsyncMock(return_value=[])
    mock_fund_repo.save_asset_quotes = AsyncMock(return_value=0)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_fund_repo", mock_fund_repo)
    try:
        result = await svc.fetch_fund_quotes("CN", ["000001"])
    finally:
        mp.undo()

    assert len(result) == 1
    assert result[0].ticker == "000001"
    # 不应该调网络
    mock_fund_repo.fetch_realtime_quote.assert_not_called()


async def test_fetch_fund_quotes_partial_cache():
    """部分缓存 + 部分走网络 → 合并返回"""
    svc = AssetQuoteService()
    cached = _make_quote("000001", asset_class="FUND", price="1.5")
    fresh = _make_quote("000002", asset_class="FUND", price="2.0")

    mock_fund_repo = AsyncMock()
    mock_fund_repo.get_recent_quotes = AsyncMock(
        return_value={"000001": cached},
    )
    mock_fund_repo.fetch_realtime_quote = AsyncMock(return_value=[fresh])
    mock_fund_repo.save_asset_quotes = AsyncMock(return_value=1)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_fund_repo", mock_fund_repo)
    try:
        result = await svc.fetch_fund_quotes("CN", ["000001", "000002"])
    finally:
        mp.undo()

    assert len(result) == 2
    tickers = {q.ticker for q in result}
    assert tickers == {"000001", "000002"}
    # 只请求缺失的
    mock_fund_repo.fetch_realtime_quote.assert_called_once_with(["000002"], market="CN")


async def test_fetch_fund_quotes_none_cached():
    """无缓存 → 全走网络"""
    svc = AssetQuoteService()
    fresh = [_make_quote("000001", asset_class="FUND", price="1.5")]

    mock_fund_repo = AsyncMock()
    mock_fund_repo.get_recent_quotes = AsyncMock(return_value={})
    mock_fund_repo.fetch_realtime_quote = AsyncMock(return_value=fresh)
    mock_fund_repo.save_asset_quotes = AsyncMock(return_value=1)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_fund_repo", mock_fund_repo)
    try:
        result = await svc.fetch_fund_quotes("CN", ["000001"])
    finally:
        mp.undo()

    assert len(result) == 1
    mock_fund_repo.fetch_realtime_quote.assert_called_once_with(["000001"], market="CN")


# ════════════════════════════════════════════════════
# fetch_stock_quotes
# ════════════════════════════════════════════════════

async def test_fetch_stock_quotes_cn():
    """CN 股票：不调 _enrich_names，设 asset_class="STOCK"，保存"""
    svc = AssetQuoteService()
    raw_quote = _make_quote("600519", market="CN", price="1800")

    mock_stock_repo = AsyncMock()
    mock_stock_repo.fetch_realtime_quote = AsyncMock(return_value=[raw_quote])
    mock_stock_repo.save_asset_quotes = AsyncMock(return_value=1)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_stock_repo", mock_stock_repo)
    try:
        result = await svc.fetch_stock_quotes("CN", ["600519"])
    finally:
        mp.undo()

    assert len(result) == 1
    assert result[0].asset_class == "STOCK"
    mock_stock_repo.save_asset_quotes.assert_called_once()


async def test_fetch_stock_quotes_us_enriches_names():
    """US 股票：调 _enrich_names 用 DB 英文名替换"""
    svc = AssetQuoteService()
    raw_quote = _make_quote("AAPL", market="US", price="170", name="苹果公司", currency="USD")

    mock_stock_repo = AsyncMock()
    mock_stock_repo.fetch_realtime_quote = AsyncMock(return_value=[raw_quote])
    mock_stock_repo.save_asset_quotes = AsyncMock(return_value=1)

    # mock _enrich_names
    async def fake_enrich(quotes):
        for q in quotes:
            q.name = "Apple Inc"

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_stock_repo", mock_stock_repo)
    mp.setattr(svc, "_enrich_names", fake_enrich)
    try:
        result = await svc.fetch_stock_quotes("US", ["AAPL"])
    finally:
        mp.undo()

    assert result[0].name == "Apple Inc"
    assert result[0].asset_class == "STOCK"


# ════════════════════════════════════════════════════
# _enrich_names
# ════════════════════════════════════════════════════

async def test_enrich_names_replaces_from_db():
    """品种表有英文名则替换，无则保留原名"""
    svc = AssetQuoteService()
    quotes = [
        _make_quote("AAPL", name="苹果"),
        _make_quote("MSFT", name="微软"),
    ]

    # mock AssetVarietyRepository.get_name_map
    mock_name_map = {"AAPL": "Apple Inc"}  # MSFT 不在 map 中
    mock_variety_repo = AsyncMock()
    mock_variety_repo.get_name_map = AsyncMock(return_value=mock_name_map)

    mp = pytest.MonkeyPatch()
    mp.setattr("app.services.asset_quote_service.AssetVarietyRepository", lambda: mock_variety_repo)
    try:
        await svc._enrich_names(quotes)
    finally:
        mp.undo()

    assert quotes[0].name == "Apple Inc"  # 替换
    assert quotes[1].name == "微软"       # 保留原名


# ════════════════════════════════════════════════════
# fetch_crypto_quotes
# ════════════════════════════════════════════════════

async def test_fetch_crypto_quotes():
    """设 asset_class="CRYPTO"，保存"""
    svc = AssetQuoteService()
    raw_quote = _make_quote("bitcoin", market="CRYPTO", price="100000", currency="USD")

    mock_crypto_repo = AsyncMock()
    mock_crypto_repo.fetch_realtime_quote = AsyncMock(return_value=[raw_quote])
    mock_crypto_repo.save_asset_quotes = AsyncMock(return_value=1)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_crypto_repo", mock_crypto_repo)
    try:
        result = await svc.fetch_crypto_quotes(["bitcoin"])
    finally:
        mp.undo()

    assert len(result) == 1
    assert result[0].asset_class == "CRYPTO"
    mock_crypto_repo.save_asset_quotes.assert_called_once()


# ════════════════════════════════════════════════════
# fetch_quotes_by_asset_class — 路由分发
# ════════════════════════════════════════════════════

async def test_fetch_quotes_by_asset_class_routing():
    """STOCK/FUND/CRYPTO 路由正确；未知类型返回空列表"""
    svc = AssetQuoteService()

    # mock 三个 fetch 方法
    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "fetch_stock_quotes", AsyncMock(return_value=["stock"]))
    mp.setattr(svc, "fetch_fund_quotes", AsyncMock(return_value=["fund"]))
    mp.setattr(svc, "fetch_crypto_quotes", AsyncMock(return_value=["crypto"]))
    try:
        assert await svc.fetch_quotes_by_asset_class("STOCK", "CN", ["A"]) == ["stock"]
        assert await svc.fetch_quotes_by_asset_class("FUND", "CN", ["B"]) == ["fund"]
        assert await svc.fetch_quotes_by_asset_class("CRYPTO", "CRYPTO", ["C"]) == ["crypto"]
        # 未知类型
        assert await svc.fetch_quotes_by_asset_class("BOND", "CN", ["D"]) == []
    finally:
        mp.undo()
