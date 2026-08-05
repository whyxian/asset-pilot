"""QuoteScheduler 单元测试 — 刷新频率判定 / 行情预热 / 失败 DB 历史兜底

不触真实网络：mock 数据源拉取、交易时段判定、汇率拉取、行情缓存。
"""

from decimal import Decimal

import pytest

from app.scheduler.quote_scheduler import QuoteScheduler


# ════════════════════════════════════════════════════
# _needs_refresh（刷新频率判定）
# ════════════════════════════════════════════════════

def test_needs_refresh_trading_hours_always(monkeypatch):
    """交易时段（含加密 7×24）→ 必刷新"""
    monkeypatch.setattr("app.scheduler.quote_scheduler.is_trading_hours", lambda m: True)
    s = QuoteScheduler()
    s._last_refresh["CN"] = 9999999999  # 刚刷过也要刷
    assert s._needs_refresh("CN") is True


def test_needs_refresh_fund_interval(monkeypatch):
    """非交易时段基金：15min 内不刷，超时刷"""
    monkeypatch.setattr("app.scheduler.quote_scheduler.is_trading_hours", lambda m: False)
    s = QuoteScheduler()
    s._last_refresh["FUND"] = 1000
    monkeypatch.setattr("app.scheduler.quote_scheduler.time.time", lambda: 1000 + 60)  # 1min 后
    assert s._needs_refresh("FUND") is False
    monkeypatch.setattr("app.scheduler.quote_scheduler.time.time", lambda: 1000 + 901)  # 15min1s 后
    assert s._needs_refresh("FUND") is True


def test_needs_refresh_stock_interval(monkeypatch):
    """非交易时段股票：30min 内不刷，超时刷；从未刷过（last=0）→ 必刷"""
    monkeypatch.setattr("app.scheduler.quote_scheduler.is_trading_hours", lambda m: False)
    s = QuoteScheduler()
    assert s._needs_refresh("CN") is True  # last 默认 0
    s._last_refresh["CN"] = 1000
    monkeypatch.setattr("app.scheduler.quote_scheduler.time.time", lambda: 1000 + 1801)  # 30min1s
    assert s._needs_refresh("CN") is True
    monkeypatch.setattr("app.scheduler.quote_scheduler.time.time", lambda: 1000 + 300)
    assert s._needs_refresh("CN") is False


# ════════════════════════════════════════════════════
# refresh_quotes（行情预热 + 失败兜底）
# ════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_refresh_quotes_no_holdings(monkeypatch):
    """无持仓 → 直接返回，不拉行情"""
    s = QuoteScheduler()
    called = []
    async def _no_groups():
        return []
    monkeypatch.setattr(s._holding_repo, "list_all_tickers", _no_groups)
    async def fake_fetch(*a, **k):
        called.append(1)
    monkeypatch.setattr(s._quote_svc, "fetch_quotes_by_asset_class", fake_fetch)
    await s.refresh_quotes()
    assert called == []


@pytest.mark.asyncio
async def test_refresh_quotes_writes_cache(monkeypatch):
    """有持仓 + 交易时段 → 拉行情写缓存"""
    s = QuoteScheduler()
    groups = {("STOCK", "CN"): ["600519"]}
    async def _groups():
        return groups
    monkeypatch.setattr(s._holding_repo, "list_all_tickers", _groups)
    monkeypatch.setattr("app.scheduler.quote_scheduler.is_trading_hours", lambda m: True)

    async def fake_fetch(ac, market, tickers, force_refresh=False):
        assert ac == "STOCK" and market == "CN" and tickers == ["600519"]
        assert force_refresh is True
        return [{"ticker": "600519"}]
    monkeypatch.setattr(s._quote_svc, "fetch_quotes_by_asset_class", fake_fetch)

    written = []
    monkeypatch.setattr("app.scheduler.quote_scheduler.quote_cache", type("QC", (), {"set": lambda self, m, q: written.append((m, q))})())

    await s.refresh_quotes()
    assert written == [("CN", [{"ticker": "600519"}])]
    assert s._last_refresh["CN"] > 0


@pytest.mark.asyncio
async def test_refresh_quotes_db_fallback_on_network_failure(monkeypatch):
    """网络失败 → 查 DB 历史兜底写缓存"""
    s = QuoteScheduler()
    groups = {("STOCK", "CN"): ["600519"]}
    async def _groups():
        return groups
    monkeypatch.setattr(s._holding_repo, "list_all_tickers", _groups)
    monkeypatch.setattr("app.scheduler.quote_scheduler.is_trading_hours", lambda m: True)

    async def boom(*a, **k):
        raise ConnectionError("网络失败")
    monkeypatch.setattr(s._quote_svc, "fetch_quotes_by_asset_class", boom)

    class FakeRepo:
        async def get_latest_quotes(self, ac, market, tickers):
            return {"600519": {"ticker": "600519", "price": Decimal("100")}}
    monkeypatch.setattr(s._quote_svc, "_get_repo", lambda ac: FakeRepo())

    written = []
    monkeypatch.setattr("app.scheduler.quote_scheduler.quote_cache", type("QC", (), {"set": lambda self, m, q: written.append((m, q))})())

    await s.refresh_quotes()  # 不应抛异常
    assert len(written) == 1
    assert written[0][0] == "CN"


@pytest.mark.asyncio
async def test_refresh_quotes_db_fallback_empty(monkeypatch):
    """网络 + DB 都无数据 → 不写缓存，不抛异常"""
    s = QuoteScheduler()
    async def _groups2():
        return {("STOCK", "CN"): ["600519"]}
    monkeypatch.setattr(s._holding_repo, "list_all_tickers", _groups2)
    monkeypatch.setattr("app.scheduler.quote_scheduler.is_trading_hours", lambda m: True)

    async def boom(*a, **k):
        raise ConnectionError("网络失败")
    monkeypatch.setattr(s._quote_svc, "fetch_quotes_by_asset_class", boom)

    class FakeRepo:
        async def get_latest_quotes(self, ac, market, tickers):
            return {}
    monkeypatch.setattr(s._quote_svc, "_get_repo", lambda ac: FakeRepo())

    written = []
    monkeypatch.setattr("app.scheduler.quote_scheduler.quote_cache", type("QC", (), {"set": lambda self, m, q: written.append((m, q))})())

    await s.refresh_quotes()
    assert written == []


# ════════════════════════════════════════════════════
# refresh_rates（汇率预热）
# ════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_refresh_rates_forces_network(monkeypatch):
    """汇率预热：force_refresh=True 绕过 1h 缓存"""
    s = QuoteScheduler()
    seen = []
    async def fake_fetch_rates(force_refresh=False):
        seen.append(force_refresh)
        return type("S", (), {"source_date": "2026-08-04", "is_stale": False})()
    monkeypatch.setattr("app.scheduler.quote_scheduler.fetch_rates", fake_fetch_rates)
    await s.refresh_rates()
    assert seen == [True]


@pytest.mark.asyncio
async def test_refresh_rates_failure_swallowed(monkeypatch):
    """汇率刷新失败 → 只记日志，不抛异常"""
    s = QuoteScheduler()
    async def boom(*a, **k):
        raise ConnectionError("网络失败")
    monkeypatch.setattr("app.scheduler.quote_scheduler.fetch_rates", boom)
    await s.refresh_rates()
