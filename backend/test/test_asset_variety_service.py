"""AssetVarietyService 单元测试 — 品种目录 CRUD + 搜索 + 软删除"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.asset_variety import AssetVarietyCreate
from app.models.orm.asset_variety_orm import AssetVarietyRecord
from app.services.asset_variety_service import AssetVarietyService


async def _count_active(Session) -> int:
    async with Session() as s:
        return (await s.execute(
            select(AssetVarietyRecord).where(AssetVarietyRecord.is_active == True)  # noqa: E712
        )).scalars().all().__len__()


async def test_create_and_list(Session):
    """新增品种 → 列表可见（只含 active）"""
    svc = AssetVarietyService()
    v = await svc.create_variety(AssetVarietyCreate(
        ticker="600519", name="贵州茅台", market="CN",
        asset_class="STOCK", currency="CNY",
    ))
    assert v.ticker == "600519"
    assert v.is_active is True

    lst = await svc.list_varieties()
    assert [x.ticker for x in lst] == ["600519"]


async def test_create_duplicate_raises(Session):
    """同三元组重复创建 → 唯一约束冲突（事务回滚）"""
    svc = AssetVarietyService()
    await svc.create_variety(AssetVarietyCreate(
        ticker="600519", name="贵州茅台", market="CN", asset_class="STOCK",
    ))
    with pytest.raises(Exception):
        await svc.create_variety(AssetVarietyCreate(
            ticker="600519", name="贵州茅台二号", market="CN", asset_class="STOCK",
        ))
    assert await _count_active(Session) == 1  # 回滚后只有一条


async def test_search_relevance(Session):
    """搜索排序：精确 ticker > ticker 前缀 > name 前缀 > 模糊"""
    svc = AssetVarietyService()
    for t, n in [("600519", "贵州茅台"), ("6005199", "茅台转债"), ("123456", "茅台概念基金")]:
        await svc.create_variety(AssetVarietyCreate(
            ticker=t, name=n, market="CN", asset_class="STOCK",
        ))

    result = await svc.search_varieties("600519")
    assert [x.ticker for x in result] == ["600519", "6005199"]  # 精确 > ticker 前缀

    result = await svc.search_varieties("茅台")
    assert [x.ticker for x in result] == ["123456", "6005199", "600519"]


async def test_soft_delete_hides_from_search(Session):
    """软删除 → 列表/搜索/精确查询都不再返回"""
    svc = AssetVarietyService()
    await svc.create_variety(AssetVarietyCreate(
        ticker="600519", name="贵州茅台", market="CN", asset_class="STOCK",
    ))

    assert await svc.delete_variety("600519") is True
    assert await _count_active(Session) == 0
    assert await svc.search_varieties("600519") == []
    assert await svc.list_varieties() == []


async def test_delete_missing_returns_false(Session):
    """删除不存在的品种 → False"""
    assert await AssetVarietyService().delete_variety("NOT_EXIST") is False
