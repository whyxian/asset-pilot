"""AssetQuoteService 单元测试 — 覆盖基金缓存策略 + 名称补全 + 路由分发

执行：
    .venv/bin/pytest test/test_asset_quote_service.py -v
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.asset_quote import AssetQuote, QuoteStatus
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
    """全部命中内存缓存 → 不调网络，返回缓存数据"""
    svc = AssetQuoteService()
    svc._cache.clear()
    # 预填内存缓存
    cached_quote = _make_quote("000001", asset_class="FUND", price="1.5")
    svc._cache.set("FUND", [cached_quote])

    mock_fund_repo = AsyncMock()
    mock_fund_repo.fetch_realtime_quote = AsyncMock(return_value=[])
    mock_fund_repo.save_asset_quotes = AsyncMock(return_value=0)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_fund_repo", mock_fund_repo)
    try:
        result = await svc.fetch_fund_quotes("CN", ["000001"])
    finally:
        mp.undo()
        svc._cache.clear()

    assert len(result) == 1
    assert result[0].ticker == "000001"
    # 不应该调网络
    mock_fund_repo.fetch_realtime_quote.assert_not_called()


async def test_fetch_fund_quotes_partial_cache():
    """部分缓存 + 部分走网络 → 合并返回，只拉缺失的"""
    svc = AssetQuoteService()
    svc._cache.clear()
    cached = _make_quote("000001", asset_class="FUND", price="1.5")
    svc._cache.set("FUND", [cached])
    fresh = _make_quote("000002", asset_class="FUND", price="2.0")

    mock_fund_repo = AsyncMock()
    mock_fund_repo.fetch_realtime_quote = AsyncMock(return_value=[fresh])
    mock_fund_repo.save_asset_quotes = AsyncMock(return_value=1)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_fund_repo", mock_fund_repo)
    try:
        result = await svc.fetch_fund_quotes("CN", ["000001", "000002"])
    finally:
        mp.undo()
        svc._cache.clear()

    assert len(result) == 2
    tickers = {q.ticker for q in result}
    assert tickers == {"000001", "000002"}
    # 只请求缺失的
    mock_fund_repo.fetch_realtime_quote.assert_called_once_with(["000002"], market="CN")


async def test_fetch_fund_quotes_none_cached():
    """无缓存 → 全走网络"""
    svc = AssetQuoteService()
    svc._cache.clear()
    fresh = [_make_quote("000001", asset_class="FUND", price="1.5")]

    mock_fund_repo = AsyncMock()
    mock_fund_repo.fetch_realtime_quote = AsyncMock(return_value=fresh)
    mock_fund_repo.save_asset_quotes = AsyncMock(return_value=1)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_fund_repo", mock_fund_repo)
    try:
        result = await svc.fetch_fund_quotes("CN", ["000001"])
    finally:
        mp.undo()
        svc._cache.clear()

    assert len(result) == 1
    mock_fund_repo.fetch_realtime_quote.assert_called_once_with(["000001"], market="CN")


async def test_fetch_fund_quotes_force_refresh_skips_cache():
    """force_refresh=True → 即使缓存命中也跳过，全部走网络拉最新，且不写缓存"""
    svc = AssetQuoteService()
    svc._cache.clear()
    cached = _make_quote("000001", asset_class="FUND", price="1.5")
    svc._cache.set("FUND", [cached])
    fresh = _make_quote("000001", asset_class="FUND", price="1.6")

    mock_fund_repo = AsyncMock()
    mock_fund_repo.fetch_realtime_quote = AsyncMock(return_value=[fresh])
    mock_fund_repo.save_asset_quotes = AsyncMock(return_value=1)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_fund_repo", mock_fund_repo)
    try:
        result = await svc.fetch_fund_quotes("CN", ["000001"], force_refresh=True)
    finally:
        mp.undo()
        svc._cache.clear()

    # 走网络拉全部
    mock_fund_repo.fetch_realtime_quote.assert_called_once_with(["000001"], market="CN")
    # 返回的是网络最新值而非缓存旧值
    assert len(result) == 1
    assert result[0].price == Decimal("1.6")


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


# ════════════════════════════════════════════════════
# fetch_quote_map_concurrent — 并发拉取 + 超时熔断 + 单组容错
# ════════════════════════════════════════════════════

async def test_fetch_quote_map_concurrent_timeout_drops_slow_group():
    """某组超时未返回 → 丢弃该组，保留已完成的组行情"""
    import asyncio
    svc = AssetQuoteService()

    async def fake_fetch(ac, market, tickers, force_refresh=False):
        if market == "US":
            return [AssetQuote(
                ticker="AAPL", asset_class="STOCK", market="US",
                name="Apple", price=Decimal("170"), currency="USD",
            )]
        await asyncio.sleep(0.5)
        return [AssetQuote(
            ticker="000001", asset_class="FUND", market="CN",
            name="华夏成长", price=Decimal("1.2"), currency="CNY",
        )]

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "fetch_quotes_by_asset_class", fake_fetch)
    # mock 降级查 DB 返回空（模拟 DB 也无历史）
    mp.setattr(svc._fund_repo, "get_latest_quotes", AsyncMock(return_value={}))
    try:
        groups = {("STOCK", "US"): ["AAPL"], ("FUND", "CN"): ["000001"]}
        quote_map = await svc.fetch_quote_map_concurrent(groups, timeout=0.1)
    finally:
        mp.undo()

    assert ("STOCK", "US", "AAPL") in quote_map
    assert quote_map[("STOCK", "US", "AAPL")][1] == QuoteStatus.REALTIME
    # 超时组降级查 DB 也无 → 不在 map
    assert ("FUND", "CN", "000001") not in quote_map


async def test_fetch_quote_map_concurrent_swallows_group_exception():
    """某组抛异常 → 不影响其他组，返回已成功组的行情"""
    svc = AssetQuoteService()

    async def fake_fetch(ac, market, tickers, force_refresh=False):
        if market == "US":
            return [AssetQuote(
                ticker="AAPL", asset_class="STOCK", market="US",
                name="Apple", price=Decimal("170"), currency="USD",
            )]
        raise RuntimeError("coinglass down")

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "fetch_quotes_by_asset_class", fake_fetch)
    # mock 降级查 DB 返回空（模拟 DB 也无历史）
    mp.setattr(svc._crypto_repo, "get_latest_quotes", AsyncMock(return_value={}))
    try:
        groups = {("STOCK", "US"): ["AAPL"], ("CRYPTO", "CRYPTO"): ["BTC"]}
        quote_map = await svc.fetch_quote_map_concurrent(groups)
    finally:
        mp.undo()

    # 实时成功的标 REALTIME
    assert ("STOCK", "US", "AAPL") in quote_map
    assert quote_map[("STOCK", "US", "AAPL")][1] == QuoteStatus.REALTIME
    # 抛异常组降级查 DB 也无 → 不在 map
    assert ("CRYPTO", "CRYPTO", "BTC") not in quote_map


async def test_fetch_quote_map_concurrent_avoids_cross_group_ticker_collision():
    """跨组 ticker 相同（如 000001 既是 A 股又是基金）→ 三元组 key 互不覆盖"""
    svc = AssetQuoteService()

    async def fake_fetch(ac, market, tickers, force_refresh=False):
        if ac == "STOCK" and market == "CN":
            return [AssetQuote(
                ticker="000001", asset_class="STOCK", market="CN",
                name="平安银行", price=Decimal("11.5"), currency="CNY",
            )]
        if ac == "FUND" and market == "CN":
            return [AssetQuote(
                ticker="000001", asset_class="FUND", market="CN",
                name="华夏成长", price=Decimal("1.2"), currency="CNY",
            )]
        return []

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "fetch_quotes_by_asset_class", fake_fetch)
    try:
        groups = {("STOCK", "CN"): ["000001"], ("FUND", "CN"): ["000001"]}
        quote_map = await svc.fetch_quote_map_concurrent(groups)
    finally:
        mp.undo()

    assert ("STOCK", "CN", "000001") in quote_map
    assert ("FUND", "CN", "000001") in quote_map
    assert quote_map[("STOCK", "CN", "000001")][0].price == Decimal("11.5")
    assert quote_map[("FUND", "CN", "000001")][0].price == Decimal("1.2")


# ════════════════════════════════════════════════════
# 行情内存缓存命中（stock/crypto 第二次调用走缓存）
# ════════════════════════════════════════════════════

async def test_fetch_stock_quotes_second_call_hits_cache():
    """同一 service 实例第二次拉相同 codes → 命中内存缓存，不调网络"""
    svc = AssetQuoteService()
    svc._cache.clear()
    raw_quote = _make_quote("600519", market="CN", price="1800")

    mock_stock_repo = AsyncMock()
    mock_stock_repo.fetch_realtime_quote = AsyncMock(return_value=[raw_quote])
    mock_stock_repo.save_asset_quotes = AsyncMock(return_value=1)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_stock_repo", mock_stock_repo)
    try:
        # 第一次：走网络，写缓存
        r1 = await svc.fetch_stock_quotes("CN", ["600519"])
        assert len(r1) == 1
        assert mock_stock_repo.fetch_realtime_quote.call_count == 1
        # 第二次：命中缓存，不再调网络
        r2 = await svc.fetch_stock_quotes("CN", ["600519"])
        assert len(r2) == 1
        assert r2[0].ticker == "600519"
        assert mock_stock_repo.fetch_realtime_quote.call_count == 1  # 仍只调 1 次
    finally:
        mp.undo()
        svc._cache.clear()


async def test_fetch_crypto_quotes_second_call_hits_cache():
    """加密货币第二次拉相同 codes → 命中缓存"""
    svc = AssetQuoteService()
    svc._cache.clear()
    raw_quote = _make_quote("bitcoin", market="CRYPTO", price="100000", currency="USD")

    mock_crypto_repo = AsyncMock()
    mock_crypto_repo.fetch_realtime_quote = AsyncMock(return_value=[raw_quote])
    mock_crypto_repo.save_asset_quotes = AsyncMock(return_value=1)

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "_crypto_repo", mock_crypto_repo)
    try:
        await svc.fetch_crypto_quotes(["bitcoin"])
        await svc.fetch_crypto_quotes(["bitcoin"])
        # 第二次命中缓存，网络只调 1 次
        assert mock_crypto_repo.fetch_realtime_quote.call_count == 1
    finally:
        mp.undo()
        svc._cache.clear()


async def test_fetch_quote_map_concurrent_partial_fallback_to_db():
    """部分 code 实时失败 → 走 DB 历史降级（HISTORICAL），成功的仍是 REALTIME"""
    import app.utils.quote_cache as qc  # 防止缓存干扰
    svc = AssetQuoteService()
    svc._cache.clear()

    async def fake_fetch(ac, market, tickers, force_refresh=False):
        # 只有 000001 成功，000002 失败（返回空）
        if "000002" in tickers:
            return [AssetQuote(
                ticker="000001", asset_class="STOCK", market="CN",
                name="平安银行", price=Decimal("11.5"), currency="CNY",
            )]
        return [AssetQuote(
            ticker="000001", asset_class="STOCK", market="CN",
            name="平安银行", price=Decimal("11.5"), currency="CNY",
        )]

    mp = pytest.MonkeyPatch()
    mp.setattr(svc, "fetch_quotes_by_asset_class", fake_fetch)
    # mock DB 历史兜底：000002 有历史行情 price=10
    historical_quote = _make_quote("000002", price="10.0")
    mp.setattr(svc._stock_repo, "get_latest_quotes", AsyncMock(
        return_value={"000002": historical_quote},
    ))
    try:
        groups = {("STOCK", "CN"): ["000001", "000002"]}
        quote_map = await svc.fetch_quote_map_concurrent(groups)
    finally:
        mp.undo()
        svc._cache.clear()

    # 000001 实时成功 → REALTIME
    assert ("STOCK", "CN", "000001") in quote_map
    assert quote_map[("STOCK", "CN", "000001")][1] == QuoteStatus.REALTIME
    assert quote_map[("STOCK", "CN", "000001")][0].price == Decimal("11.5")
    # 000002 实时失败 → DB 历史降级 → HISTORICAL
    assert ("STOCK", "CN", "000002") in quote_map
    assert quote_map[("STOCK", "CN", "000002")][1] == QuoteStatus.HISTORICAL
    assert quote_map[("STOCK", "CN", "000002")][0].price == Decimal("10.0")
