"""AssetQuoteRepository 单元测试 — 覆盖 save_asset_quotes 去重 + get_recent_quotes 缓存查询

通过 StockQuoteRepository（具体子类）测试基类的共享方法。
不需要调网络，mock 掉 fetch_realtime_quote 即可。

执行：
    .venv/bin/pytest test/test_asset_quote_repository.py -v
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.models.asset_quote import AssetQuote
from app.repositories.asset_quote_repository import StockQuoteRepository


def _make_quote(ticker: str, price: str = "10", **kw) -> AssetQuote:
    """构造 AssetQuote 测试数据"""
    defaults = dict(
        ticker=ticker, asset_class="STOCK", market="CN", name=ticker,
        price=Decimal(price), currency="CNY", source="TEST",
    )
    defaults.update(kw)
    return AssetQuote(**defaults)


async def test_save_inserts_new(Session, seed_quote):
    """新行情插入成功，rowcount 正确"""
    repo = StockQuoteRepository()
    # mock 掉 fetch（不测网络）
    repo._tencent.fetch = AsyncMock(return_value=[])
    repo._sina.fetch = AsyncMock(return_value=[])

    quotes = [_make_quote("600519", price="1800"), _make_quote("000001", price="12")]
    saved = await repo.save_asset_quotes(quotes)
    assert saved == 2


async def test_save_ignores_duplicate(Session, seed_quote):
    """同 (asset_class, market, ticker, timestamp) 重复插入被跳过"""
    now = datetime.now()
    quote = _make_quote("600519", price="1800", updated_at=now)

    repo = StockQuoteRepository()
    repo._tencent.fetch = AsyncMock(return_value=[])
    repo._sina.fetch = AsyncMock(return_value=[])

    # 第一次插入成功
    saved1 = await repo.save_asset_quotes([quote])
    assert saved1 == 1

    # 同一 quote 再次插入 → 被跳过（INSERT OR IGNORE）
    saved2 = await repo.save_asset_quotes([quote])
    assert saved2 == 0


async def test_get_recent_quotes_dedup(Session, seed_quote):
    """同 ticker 多条记录 → 只返回最新一条（按 created_at 倒序取第一条）"""
    now = datetime.now()
    # 插入两条同 ticker 不同时间的行情（手动插入以控制 created_at）
    await seed_quote(ticker="600519", price="1700", created_at=now - timedelta(minutes=5))
    await seed_quote(ticker="600519", price="1800", created_at=now - timedelta(minutes=1))

    repo = StockQuoteRepository()
    repo._tencent.fetch = AsyncMock(return_value=[])
    repo._sina.fetch = AsyncMock(return_value=[])

    result = await repo.get_recent_quotes("STOCK", "CN", ["600519"], max_age_minutes=15)
    assert "600519" in result
    # 应该返回最新的那条（price=1800）
    assert result["600519"].price == Decimal("1800")


async def test_get_recent_quotes_cutoff(Session, seed_quote):
    """超过 max_age_minutes 的不返回"""
    old_time = datetime.now() - timedelta(minutes=30)
    await seed_quote(ticker="600519", price="1700", created_at=old_time)

    repo = StockQuoteRepository()
    repo._tencent.fetch = AsyncMock(return_value=[])
    repo._sina.fetch = AsyncMock(return_value=[])

    result = await repo.get_recent_quotes("STOCK", "CN", ["600519"], max_age_minutes=15)
    assert "600519" not in result
