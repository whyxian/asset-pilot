"""汇率工具单元测试 — 覆盖 fetch_rates 缓存/降级 + to_cny 转换/边界

执行：
    .venv/bin/pytest test/test_exchange_rate.py -v
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.utils.exchange_rate import RatesSnapshot, fetch_rates, to_cny


# ════════════════════════════════════════════════════
# to_cny
# ════════════════════════════════════════════════════

async def test_to_cny_same_currency():
    """from_currency="CNY" → 直接返回原值，不调 fetch_rates"""
    assert await to_cny(Decimal("100"), "CNY") == Decimal("100")


async def test_to_cny_normal_conversion():
    """USD→CNY：amount / src_rate * cny_rate"""
    import app.utils.exchange_rate as er

    fake_rates = {"CNY": 6.7674, "USD": 1.0, "EUR": 0.8672}
    # 预填缓存，绕过网络
    er._cache = {"rates": fake_rates, "fetched_at": 9999999999, "source_date": None, "is_stale": False}

    result = await to_cny(Decimal("100"), "USD")
    # 100 / 1.0 * 6.7674 = 676.74
    assert abs(result - Decimal("676.74")) < Decimal("0.01")


async def test_to_cny_unknown_currency():
    """汇率表缺目标货币 → 返回原值"""
    import app.utils.exchange_rate as er

    fake_rates = {"CNY": 6.7674, "USD": 1.0}
    er._cache = {"rates": fake_rates, "fetched_at": 9999999999, "source_date": None, "is_stale": False}

    # GBP 不在汇率表里
    result = await to_cny(Decimal("100"), "GBP")
    assert result == Decimal("100")


# ════════════════════════════════════════════════════
# fetch_rates
# ════════════════════════════════════════════════════

async def test_fetch_rates_success():
    """mock httpx 返回正常 JSON → 缓存写入内存 + 落盘，返回 RatesSnapshot（fresh）"""
    import app.utils.exchange_rate as er

    er._cache = {"rates": None, "fetched_at": 0, "source_date": None, "is_stale": False}

    mock_response = MagicMock()
    mock_response.json.return_value = {"datas": {"CNY": 6.7674, "USD": 1.0}, "date": "2026-06-15"}
    # 模拟 async context manager
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    persist_calls = []
    with pytest.MonkeyPatch.context() as m:
        m.setattr("httpx.AsyncClient", lambda **kw: mock_client)
        m.setattr("app.utils.exchange_rate._persist", lambda rates, src: persist_calls.append((rates, src)))
        result = await fetch_rates()

    assert isinstance(result, RatesSnapshot)
    assert "CNY" in result.rates
    assert result.source_date == "2026-06-15"
    assert result.is_stale is False  # 网络成功 → 新鲜
    assert er._cache["rates"] is not None
    assert er._cache["source_date"] == "2026-06-15"
    # 成功拉取后应落盘作为兜底
    assert len(persist_calls) == 1
    assert persist_calls[0][1] == "2026-06-15"


async def test_fetch_rates_single_flight():
    """N 个并发请求同时触发网络拉取 → 单飞，只发 1 个网络请求"""
    import asyncio
    import app.utils.exchange_rate as er

    er._cache = {"rates": None, "fetched_at": 0, "source_date": None, "is_stale": False}
    er._inflight = None

    mock_response = MagicMock()
    mock_response.json.return_value = {"datas": {"CNY": 6.7674, "USD": 1.0}, "date": "2026-06-15"}
    mock_client = AsyncMock()
    get_call_count = 0
    async def slow_get(*a, **kw):
        nonlocal get_call_count
        get_call_count += 1
        await asyncio.sleep(0.05)  # 模拟慢请求，让并发请求有时间叠加
        return mock_response
    mock_client.get = slow_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with pytest.MonkeyPatch.context() as m:
        m.setattr("httpx.AsyncClient", lambda **kw: mock_client)
        m.setattr("app.utils.exchange_rate._persist", lambda rates, src: None)
        # 5 个并发请求
        results = await asyncio.gather(*[fetch_rates() for _ in range(5)])

    # 5 个请求都拿到结果
    assert all(isinstance(r, RatesSnapshot) for r in results)
    assert all(r.source_date == "2026-06-15" for r in results)
    # 但网络只被调用 1 次（单飞）
    assert get_call_count == 1


async def test_fetch_rates_cache_hit():
    """缓存未过期 → 直接返回 RatesSnapshot，不再请求网络"""
    import app.utils.exchange_rate as er
    import time

    fake_rates = {"CNY": 6.7674}
    er._cache = {"rates": fake_rates, "fetched_at": time.time(), "source_date": "2026-06-15", "is_stale": False}

    # 不 mock httpx — 如果走到网络会超时/报错，但我们预期它不会走网络
    result = await fetch_rates()
    assert isinstance(result, RatesSnapshot)
    assert result.rates == fake_rates
    assert result.is_stale is False


async def test_fetch_rates_network_failure():
    """httpx 异常 + 内存空 + 磁盘空 → 返回硬编码兜底（永不 None）"""
    import app.utils.exchange_rate as er

    er._cache = {"rates": None, "fetched_at": 0, "source_date": None, "is_stale": False}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("网络超时"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with pytest.MonkeyPatch.context() as m:
        m.setattr("httpx.AsyncClient", lambda **kw: mock_client)
        m.setattr("app.utils.exchange_rate._load_persisted", lambda: None)
        result = await fetch_rates()

    # 五级兜底：网络/内存/磁盘都不可用 → 硬编码常量兜底，不返回 None，且标记 stale
    assert isinstance(result, RatesSnapshot)
    assert result.rates is er._HARDCODED_RATES
    assert result.source_date == er._HARDCODED_SOURCE_DATE
    assert result.is_stale is True
    assert "USD" in result.rates and "CNY" in result.rates


async def test_fetch_rates_falls_back_to_expired_memory():
    """网络失败 + 内存有过期旧值 → 返回内存过期值兜底（stale）"""
    import app.utils.exchange_rate as er

    stale = {"CNY": 6.7674, "USD": 1.0}
    er._cache = {"rates": stale, "fetched_at": 0, "source_date": "2026-06-10", "is_stale": False}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("网络超时"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with pytest.MonkeyPatch.context() as m:
        m.setattr("httpx.AsyncClient", lambda **kw: mock_client)
        result = await fetch_rates()

    assert isinstance(result, RatesSnapshot)
    assert result.rates == stale
    assert result.source_date == "2026-06-10"
    assert result.is_stale is True


async def test_fetch_rates_falls_back_to_disk_on_restart():
    """网络失败 + 内存空（重启后首次）+ 磁盘有旧值 → 返回磁盘值并回填内存（stale）"""
    import app.utils.exchange_rate as er

    er._cache = {"rates": None, "fetched_at": 0, "source_date": None, "is_stale": False}
    persisted = ({"CNY": 7.1, "USD": 1.0}, "2026-06-18")

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("网络超时"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with pytest.MonkeyPatch.context() as m:
        m.setattr("httpx.AsyncClient", lambda **kw: mock_client)
        m.setattr("app.utils.exchange_rate._load_persisted", lambda: persisted)
        result = await fetch_rates()

    assert isinstance(result, RatesSnapshot)
    assert result.rates == {"CNY": 7.1, "USD": 1.0}
    assert result.source_date == "2026-06-18"
    assert result.is_stale is True
    # 磁盘值回填内存，避免反复读盘
    assert er._cache["rates"] == {"CNY": 7.1, "USD": 1.0}


# ════════════════════════════════════════════════════
# _load_persisted — 运行时缓存优先，回退种子文件
# ════════════════════════════════════════════════════

def test_load_persisted_falls_back_to_seed():
    """运行时缓存不存在 → 回退到仓库内的种子文件（全新环境也有兜底）"""
    import json
    import os
    import tempfile
    from pathlib import Path

    import app.utils.exchange_rate as er

    # 运行时缓存不存在（全新环境 / 容器无持久卷），种子文件在仓库里
    with pytest.MonkeyPatch.context() as m:
        m.setattr("app.utils.exchange_rate._PERSIST_PATH", er._FALLBACK_PATH.parent / "__nonexistent_runtime__.json")
        result = er._load_persisted()

    assert result is not None
    rates, source_date = result
    # 种子文件含 USD 为基准的汇率（CNY≈6.76，USD=1），日期取文件 date 字段
    assert "USD" in rates and "CNY" in rates
    assert rates["USD"] == 1
    assert source_date == "2026-06-18"


def test_load_persisted_prefers_runtime_cache_over_seed():
    """运行时缓存存在 → 用运行时缓存（较新），不读种子"""
    import json
    import os
    import tempfile
    from pathlib import Path

    import app.utils.exchange_rate as er

    runtime_rates = {"CNY": 7.2, "USD": 1.0}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"rates": runtime_rates, "source_date": "2026-06-19"}, f)
        runtime_path = f.name

    try:
        with pytest.MonkeyPatch.context() as m:
            m.setattr("app.utils.exchange_rate._PERSIST_PATH", Path(runtime_path))
            result = er._load_persisted()
        assert result is not None
        rates, source_date = result
        assert rates == runtime_rates
        assert source_date == "2026-06-19"
    finally:
        os.unlink(runtime_path)
