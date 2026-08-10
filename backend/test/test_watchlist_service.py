"""WatchlistService 单元测试 — 收藏/自动注册品种/幂等/取消/with-quotes 三态"""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.asset_quote import AssetQuote, QuoteStatus
from app.models.asset_watchlist import WatchlistCreate
from app.models.orm.asset_variety_orm import AssetVarietyRecord
from app.models.orm.asset_watchlist_orm import WatchlistRecord
from app.services.watchlist_service import WatchlistService


async def _count(Session, model) -> int:
    async with Session() as s:
        return (await s.execute(select(func.count()).select_from(model))).scalar()


# ════════════════════════════════════════════════════
# 收藏 + 自动注册品种
# ════════════════════════════════════════════════════

async def test_create_watchlist_auto_registers_variety(Session):
    """收藏品种表不存在的代码 → 自动注册到 asset_varieties"""
    svc = WatchlistService()
    item = await svc.create_watchlist(WatchlistCreate(
        ticker="SHIB", name="Shiba Inu", market="CRYPTO", asset_class="CRYPTO",
    ))
    assert item.id > 0
    assert await _count(Session, WatchlistRecord) == 1
    # 品种被自动注册
    assert await _count(Session, AssetVarietyRecord) == 1
    async with Session() as s:
        v = (await s.execute(select(AssetVarietyRecord))).scalar_one()
        assert v.ticker == "SHIB"
        assert v.asset_class == "CRYPTO"
        assert v.is_active is True


async def test_create_watchlist_existing_variety_not_duplicated(Session, seed_variety):
    """品种已存在 → 收藏时不再重复注册"""
    await seed_variety(ticker="600519", asset_class="STOCK", market="CN", name="贵州茅台")
    svc = WatchlistService()
    await svc.create_watchlist(WatchlistCreate(
        ticker="600519", name="贵州茅台", market="CN", asset_class="STOCK",
    ))
    assert await _count(Session, AssetVarietyRecord) == 1  # 不重复


async def test_create_watchlist_us_aligns_variety_class(Session, seed_variety):
    """US 收藏分类对齐：SPY 以 STOCK 查询、库里是 FUND → 收藏记录用 FUND，不注册新分类

    2026-08-10 市场规则（用户确认）：US/CRYPTO ticker 不重复，收藏时对齐库里已有分类。
    """
    await seed_variety(ticker="SPY", asset_class="FUND", market="US", name="SPDR S&P 500 ETF")
    svc = WatchlistService()
    item = await svc.create_watchlist(WatchlistCreate(
        ticker="SPY", name="SPY", market="US", asset_class="STOCK",  # 前端误识别为 STOCK
    ))
    assert item.asset_class == "FUND"  # 对齐库里分类
    assert item.market == "US"
    assert item.name == "SPDR S&P 500 ETF"  # 名称也用库里的
    # 品种库不产生新分类的 SPY（US 不重复规则）
    async with Session() as s:
        rows = (await s.execute(select(AssetVarietyRecord).where(
            AssetVarietyRecord.ticker == "SPY", AssetVarietyRecord.is_active == True,  # noqa: E712
        ))).scalars().all()
        assert len(rows) == 1
        assert rows[0].asset_class == "FUND"


async def test_create_watchlist_cn_keeps_triple(Session, seed_variety):
    """CN 收藏保持三元组：000001 股票与基金不同分类，不互相对齐"""
    await seed_variety(ticker="000001", asset_class="STOCK", market="CN", name="平安银行")
    svc = WatchlistService()
    # 以基金分类收藏 000001 → 库里只有股票 → 注册基金分类，不覆盖股票
    item = await svc.create_watchlist(WatchlistCreate(
        ticker="000001", name="平安银行", market="CN", asset_class="FUND",
    ))
    assert item.asset_class == "FUND"
    async with Session() as s:
        rows = (await s.execute(select(AssetVarietyRecord).where(
            AssetVarietyRecord.ticker == "000001", AssetVarietyRecord.is_active == True,  # noqa: E712
        ))).scalars().all()
        assert len(rows) == 2  # 股票 + 基金并存（CN 允许重复）


async def test_create_watchlist_idempotent(Session):
    """重复收藏同一代码 → 幂等返回已有记录，不产生重复行"""
    svc = WatchlistService()
    payload = WatchlistCreate(ticker="BTC", name="Bitcoin", market="CRYPTO", asset_class="CRYPTO")
    first = await svc.create_watchlist(payload)
    second = await svc.create_watchlist(payload)
    assert second.id == first.id
    assert await _count(Session, WatchlistRecord) == 1


# ════════════════════════════════════════════════════
# 取消收藏
# ════════════════════════════════════════════════════

async def test_delete_watchlist_keeps_variety(Session):
    """取消收藏 → 仅删 watchlist，品种库保留"""
    svc = WatchlistService()
    item = await svc.create_watchlist(WatchlistCreate(
        ticker="BTC", name="Bitcoin", market="CRYPTO", asset_class="CRYPTO",
    ))
    assert await svc.delete_watchlist(item.id) is True
    assert await _count(Session, WatchlistRecord) == 0
    assert await _count(Session, AssetVarietyRecord) == 1  # 品种保留


async def test_delete_missing_returns_false(Session):
    assert await WatchlistService().delete_watchlist(999) is False


# ════════════════════════════════════════════════════
# 列表 + with-quotes 三态
# ════════════════════════════════════════════════════

async def test_list_watchlist_order(Session):
    """列表：后收藏的排前面（id 倒序）"""
    svc = WatchlistService()
    a = await svc.create_watchlist(WatchlistCreate(ticker="AAA", name="A", market="CN", asset_class="STOCK"))
    await svc.create_watchlist(WatchlistCreate(ticker="BBB", name="B", market="CN", asset_class="STOCK"))
    items = await svc.list_watchlist()
    assert [x.ticker for x in items] == ["BBB", "AAA"]
    assert items[0].id > a.id


async def test_list_with_quotes_empty(Session):
    """无自选 → 空列表"""
    assert await WatchlistService().list_with_quotes() == []


async def test_list_with_quotes_three_state(Session, monkeypatch):
    # ⚠️ 必须依赖 Session：本测试调用 create_watchlist（写库），
    # 没有 Session 时 conftest 的 async_session patch 不建立，会写入真实数据库！
    """with-quotes：实时/历史/UNAVAILABLE 三态透传"""
    svc = WatchlistService()
    # 直接插 3 条自选（不同 ticker）
    for t in ("AAA", "BBB", "CCC"):
        await svc.create_watchlist(WatchlistCreate(ticker=t, name=t, market="CN", asset_class="STOCK"))

    async def fake_quote_map(groups, **kw):
        return {
            ("STOCK", "CN", "AAA"): (_quote("AAA", "10"), QuoteStatus.REALTIME),
            ("STOCK", "CN", "BBB"): (_quote("BBB", "20"), QuoteStatus.HISTORICAL),
            # CCC 不在 map → UNAVAILABLE
        }
    monkeypatch.setattr(svc._quote_svc, "fetch_quote_map_concurrent", fake_quote_map)

    result = await svc.list_with_quotes()
    by_ticker = {x.ticker: x for x in result}
    assert by_ticker["AAA"].status == QuoteStatus.REALTIME
    assert by_ticker["AAA"].quote.price == Decimal("10")
    assert by_ticker["BBB"].status == QuoteStatus.HISTORICAL
    assert by_ticker["CCC"].status == QuoteStatus.UNAVAILABLE
    assert by_ticker["CCC"].quote is None


def _quote(ticker: str, price: str) -> AssetQuote:
    return AssetQuote(
        ticker=ticker, asset_class="STOCK", market="CN", name=ticker,
        price=Decimal(price), currency="CNY", source="TEST",
    )
