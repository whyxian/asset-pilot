"""汇率工具单元测试 — 覆盖 fetch_rates 缓存/降级 + to_cny 转换/边界

执行：
    .venv/bin/pytest test/test_exchange_rate.py -v
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.utils.exchange_rate import fetch_rates, to_cny


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
    er._cache = {"rates": fake_rates, "fetched_at": 9999999999}

    result = await to_cny(Decimal("100"), "USD")
    # 100 / 1.0 * 6.7674 = 676.74
    assert abs(result - Decimal("676.74")) < Decimal("0.01")


async def test_to_cny_rates_unavailable():
    """fetch_rates 返回 None → 返回原值不报错"""
    mp = pytest.MonkeyPatch()
    mp.setattr("app.utils.exchange_rate.fetch_rates", AsyncMock(return_value=None))
    try:
        result = await to_cny(Decimal("100"), "USD")
    finally:
        mp.undo()

    assert result == Decimal("100")


async def test_to_cny_unknown_currency():
    """汇率表缺目标货币 → 返回原值"""
    import app.utils.exchange_rate as er

    fake_rates = {"CNY": 6.7674, "USD": 1.0}
    er._cache = {"rates": fake_rates, "fetched_at": 9999999999}

    # GBP 不在汇率表里
    result = await to_cny(Decimal("100"), "GBP")
    assert result == Decimal("100")


# ════════════════════════════════════════════════════
# fetch_rates
# ════════════════════════════════════════════════════

async def test_fetch_rates_success():
    """mock httpx 返回正常 JSON → 缓存写入，返回 dict"""
    import app.utils.exchange_rate as er

    er._cache = {"rates": None, "fetched_at": 0}

    mock_response = MagicMock()
    mock_response.json.return_value = {"datas": {"CNY": 6.7674, "USD": 1.0}, "date": "2026-06-15"}
    # 模拟 async context manager
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with pytest.MonkeyPatch.context() as m:
        m.setattr("httpx.AsyncClient", lambda **kw: mock_client)
        result = await fetch_rates()

    assert result is not None
    assert "CNY" in result
    assert er._cache["rates"] is not None


async def test_fetch_rates_cache_hit():
    """缓存未过期 → 直接返回，不再请求网络"""
    import app.utils.exchange_rate as er
    import time

    fake_rates = {"CNY": 6.7674}
    er._cache = {"rates": fake_rates, "fetched_at": time.time()}

    # 不 mock httpx — 如果走到网络会超时/报错，但我们预期它不会走网络
    result = await fetch_rates()
    assert result == fake_rates


async def test_fetch_rates_network_failure():
    """httpx 异常 + 无旧缓存 → 返回 None"""
    import app.utils.exchange_rate as er

    er._cache = {"rates": None, "fetched_at": 0}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("网络超时"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with pytest.MonkeyPatch.context() as m:
        m.setattr("httpx.AsyncClient", lambda **kw: mock_client)
        result = await fetch_rates()

    assert result is None
