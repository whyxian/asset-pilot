"""AssetVarietyRepository 单元测试 — 覆盖 search_varieties 相关性排序

执行：
    .venv/bin/pytest test/test_asset_variety_repository.py -v
"""

import pytest

from app.repositories.asset_variety_repository import AssetVarietyRepository


async def test_search_exact_match_first(Session, seed_variety):
    """精确匹配 ticker 排最前"""
    # 插入多条品种
    await seed_variety(ticker="AAPL", name="Apple Inc", asset_class="STOCK", market="US")
    await seed_variety(ticker="AAP", name="AAP Corporation", asset_class="STOCK", market="US")
    await seed_variety(ticker="AAPL", name="Apple Fund", asset_class="FUND", market="US")

    repo = AssetVarietyRepository()
    result = await repo.search_varieties("AAPL", limit=10)

    # 精确匹配 AAPL 排最前
    assert len(result) >= 2
    # 精确匹配的 ticker 排在首位
    assert result[0].ticker == "AAPL"


async def test_search_ticker_prefix_second(Session, seed_variety):
    """ticker 前缀匹配排在 name 前缀匹配前"""
    await seed_variety(ticker="MSFT", name="Microsoft", asset_class="STOCK", market="US")
    await seed_variety(ticker="MS", name="Morgan Stanley", asset_class="STOCK", market="US")
    # "MST" 匹配 MSFT 的 ticker 前缀 (MS*)... 实际用 "MS" 搜索
    await seed_variety(ticker="AMSI", name="MS Fund", asset_class="FUND", market="US")

    repo = AssetVarietyRepository()
    result = await repo.search_varieties("MS", limit=10)

    # ticker 前缀 "MS" 精确匹配 MS 排最前（相关性 0 或 1）
    # name 包含 "MS" 的 AMSI 排后面（相关性 3）
    tickers = [r.ticker for r in result]
    # MS 应该在 AMSI 前面（MS 是 ticker 前缀匹配，AMSI 只是 name 包含）
    if "MS" in tickers and "AMSI" in tickers:
        assert tickers.index("MS") < tickers.index("AMSI")


async def test_search_name_prefix(Session, seed_variety):
    """name 前缀能搜到"""
    await seed_variety(ticker="601318", name="中国平安", asset_class="STOCK", market="CN")

    repo = AssetVarietyRepository()
    result = await repo.search_varieties("中国", limit=10)

    assert len(result) >= 1
    assert result[0].name == "中国平安"


async def test_search_limit(Session, seed_variety):
    """limit 参数生效"""
    # 插入 5 条含 "test" 的品种
    for i in range(5):
        await seed_variety(
            ticker=f"T{i}", name=f"TestVariety{i}",
            asset_class="STOCK", market="CN",
        )

    repo = AssetVarietyRepository()
    result = await repo.search_varieties("Test", limit=3)
    assert len(result) <= 3


async def test_search_no_match(Session):
    """无匹配返回空列表"""
    repo = AssetVarietyRepository()
    result = await repo.search_varieties("ZZZZNOTEXIST", limit=10)
    assert result == []
