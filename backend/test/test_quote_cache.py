"""QuoteCache 单元测试 — 覆盖 get/set/过期/部分命中/跨市场隔离

执行：
    .venv/bin/pytest test/test_quote_cache.py -v
"""

import time
from decimal import Decimal

from app.models.asset_quote import AssetQuote
from app.utils.quote_cache import QuoteCache


def _make_quote(ticker: str, price: str = "10") -> AssetQuote:
    return AssetQuote(
        ticker=ticker, asset_class="STOCK", market="CN", name=ticker,
        price=Decimal(price), currency="CNY", source="TEST",
    )


# ════════════════════════════════════════════════════
# get / set
# ════════════════════════════════════════════════════

def test_miss_when_empty():
    """空缓存 → 全部缺失"""
    cache = QuoteCache()
    hit, missing = cache.get("CN", ["000001", "000002"])
    assert hit == {}
    assert missing == ["000001", "000002"]


def test_hit_after_set():
    """写入后命中"""
    cache = QuoteCache()
    cache.set("CN", [_make_quote("000001", "1.5")])
    hit, missing = cache.get("CN", ["000001"])
    assert "000001" in hit
    assert hit["000001"].price == Decimal("1.5")
    assert missing == []


def test_partial_hit():
    """部分命中：3 只里 1 只命中，2 只缺失"""
    cache = QuoteCache()
    cache.set("CN", [_make_quote("000001", "1.5")])
    hit, missing = cache.get("CN", ["000001", "000002", "000003"])
    assert set(hit.keys()) == {"000001"}
    assert set(missing) == {"000002", "000003"}


def test_cross_market_isolation():
    """同 ticker 不同市场互不干扰（000001 既是 A 股又是基金）"""
    cache = QuoteCache()
    stock_q = _make_quote("000001", "11.5")
    stock_q.asset_class = "STOCK"
    fund_q = _make_quote("000001", "1.2")
    fund_q.asset_class = "FUND"
    cache.set("CN", [stock_q])
    cache.set("FUND", [fund_q])

    hit_cn, _ = cache.get("CN", ["000001"])
    hit_fund, _ = cache.get("FUND", ["000001"])
    assert hit_cn["000001"].price == Decimal("11.5")
    assert hit_fund["000001"].price == Decimal("1.2")


# ════════════════════════════════════════════════════
# 过期
# ════════════════════════════════════════════════════

def test_expired_entry_treated_as_missing():
    """过期项视为缺失，且被清除"""
    cache = QuoteCache()
    cache.set("CN", [_make_quote("000001", "1.5")])
    # 手动把过期时间改到过去
    key = ("CN", "000001")
    cache._store[key] = (cache._store[key][0], time.time() - 1)

    hit, missing = cache.get("CN", ["000001"])
    assert hit == {}
    assert missing == ["000001"]
    # 过期项应被清除
    assert key not in cache._store


# ════════════════════════════════════════════════════
# clear
# ════════════════════════════════════════════════════

def test_clear_empties_cache():
    """clear 清空全部缓存"""
    cache = QuoteCache()
    cache.set("CN", [_make_quote("000001")])
    cache.set("FUND", [_make_quote("000002")])
    cache.clear()
    hit, missing = cache.get("CN", ["000001"])
    assert hit == {}
    assert missing == ["000001"]
