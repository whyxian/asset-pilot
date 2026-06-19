"""交易时段判定单元测试 — 覆盖 is_trading_hours + quote_cache_ttl

执行：
    .venv/bin/pytest test/test_trading_hours.py -v
"""

from datetime import datetime

from app.utils.trading_hours import is_trading_hours, quote_cache_ttl


# ════════════════════════════════════════════════════
# is_trading_hours
# ════════════════════════════════════════════════════

def test_crypto_always_trading():
    """加密货币 7×24 全天候交易"""
    # 任意时刻都为 True
    assert is_trading_hours("CRYPTO", datetime(2026, 6, 15, 0, 0))    # 周一凌晨
    assert is_trading_hours("CRYPTO", datetime(2026, 6, 21, 12, 0))   # 周日中午
    assert is_trading_hours("CRYPTO", datetime(2026, 6, 19, 3, 30))   # 任意


def test_cn_trading_session():
    """A股交易时段：工作日 9:30-11:30 / 13:00-15:00"""
    monday = datetime(2026, 6, 15)  # 周一
    # 上午盘 9:30-11:30
    assert is_trading_hours("CN", datetime(2026, 6, 15, 9, 30))
    assert is_trading_hours("CN", datetime(2026, 6, 15, 11, 29))
    assert not is_trading_hours("CN", datetime(2026, 6, 15, 11, 30))  # 收盘
    # 下午盘 13:00-15:00
    assert is_trading_hours("CN", datetime(2026, 6, 15, 13, 0))
    assert is_trading_hours("CN", datetime(2026, 6, 15, 14, 59))
    assert not is_trading_hours("CN", datetime(2026, 6, 15, 15, 0))   # 收盘
    # 午休 11:30-13:00
    assert not is_trading_hours("CN", datetime(2026, 6, 15, 12, 0))


def test_cn_weekend_closed():
    """A股周末休市"""
    saturday = datetime(2026, 6, 20, 10, 0)  # 周六上午
    sunday = datetime(2026, 6, 21, 14, 0)    # 周日下午
    assert not is_trading_hours("CN", saturday)
    assert not is_trading_hours("CN", sunday)


def test_us_trading_session():
    """美股交易时段：北京时间 21:30-次日 04:00（跨日）"""
    monday = datetime(2026, 6, 15)
    # 21:30 开盘
    assert is_trading_hours("US", datetime(2026, 6, 15, 21, 30))
    assert is_trading_hours("US", datetime(2026, 6, 15, 23, 59))
    # 跨日到次日 04:00
    assert is_trading_hours("US", datetime(2026, 6, 16, 0, 0))
    assert is_trading_hours("US", datetime(2026, 6, 16, 3, 59))
    assert not is_trading_hours("US", datetime(2026, 6, 16, 4, 0))    # 收盘
    # 盘外
    assert not is_trading_hours("US", datetime(2026, 6, 15, 10, 0))


def test_us_weekend_closed():
    """美股周末休市（按北京时间工作日判定，简化）"""
    assert not is_trading_hours("US", datetime(2026, 6, 20, 22, 0))  # 周六


def test_unknown_market_not_trading():
    """未知市场默认非交易时段"""
    assert not is_trading_hours("UNKNOWN", datetime(2026, 6, 15, 10, 0))


# ════════════════════════════════════════════════════
# quote_cache_ttl
# ════════════════════════════════════════════════════

def test_ttl_uniform_5min_safety_net():
    """TTL 统一 5min 兜底（定时任务 30s 刷新保证新鲜度，TTL 仅调度器故障时触发）"""
    assert quote_cache_ttl("FUND") == 300
    assert quote_cache_ttl("CRYPTO") == 300
    assert quote_cache_ttl("CN") == 300
    assert quote_cache_ttl("US") == 300


def test_trading_hours_cn():
    """A股时段判定（与 TTL 无关，仍用于 scheduler 频率决策）"""
    assert is_trading_hours("CN", datetime(2026, 6, 15, 10, 0))  # 交易中
    assert not is_trading_hours("CN", datetime(2026, 6, 15, 16, 0))  # 收盘后
