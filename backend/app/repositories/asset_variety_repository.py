"""品种目录数据访问 — asset_varieties 表 CRUD"""

from sqlalchemy import select

from app.core.database import async_session
from app.models.asset_variety import AssetVariety, AssetVarietyCreate
from app.models.orm.asset_variety_orm import AssetVarietyRecord


class AssetVarietyRepository:
    """品种目录数据访问"""

    async def list_varieties(self) -> list[AssetVariety]:
        """获取全部品种"""
        async with async_session() as session:
            records = (await session.execute(
                select(AssetVarietyRecord).where(AssetVarietyRecord.is_active == True)
            )).scalars().all()
            return [_record_to_variety(r) for r in records]

    async def search_varieties(self, query: str, limit: int = 10) -> list[AssetVariety]:
        """搜索品种（按 ticker 或名称模糊匹配）

        Args:
            query: 搜索关键词
            limit: 返回条数上限
        """
        pattern = f"%{query}%"
        async with async_session() as session:
            records = (await session.execute(
                select(AssetVarietyRecord)
                .where(
                    AssetVarietyRecord.is_active == True,
                    (AssetVarietyRecord.ticker.like(pattern)) |
                    (AssetVarietyRecord.name.like(pattern)),
                )
                .limit(limit)
            )).scalars().all()
            return [_record_to_variety(r) for r in records]

    async def get_variety(self, ticker: str, asset_class: str | None = None, market: str | None = None) -> AssetVariety | None:
        """按代码查询品种（可指定 asset_class + market 精确匹配）

        Args:
            ticker: 标的代码
            asset_class: 资产类别，如 "STOCK" / "FUND" / "ETF"（可选）
            market: 市场，如 "CN" / "US"（可选）
        """
        async with async_session() as session:
            stmt = select(AssetVarietyRecord).where(
                AssetVarietyRecord.ticker == ticker,
                AssetVarietyRecord.is_active == True,
            )
            if asset_class:
                stmt = stmt.where(AssetVarietyRecord.asset_class == asset_class)
            if market:
                stmt = stmt.where(AssetVarietyRecord.market == market)
            r = (await session.execute(stmt)).scalar_one_or_none()
            return _record_to_variety(r) if r else None

    async def create_variety(self, data: AssetVarietyCreate) -> AssetVariety:
        """新增品种"""
        record = AssetVarietyRecord(
            ticker=data.ticker,
            name=data.name,
            market=data.market,
            asset_class=data.asset_class,
            sub_category=data.sub_category,
            currency=data.currency,
        )
        async with async_session() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return _record_to_variety(record)

    async def get_name_map(self, tickers: list[str]) -> dict[str, str]:
        """批量查询品种名称映射（ticker → name）

        Args:
            tickers: 标的代码列表

        Returns:
            {ticker: name, ...}，只返回存在的品种
        """
        async with async_session() as session:
            result = await session.execute(
                select(AssetVarietyRecord.ticker, AssetVarietyRecord.name).where(
                    AssetVarietyRecord.ticker.in_(tickers)
                )
            )
            return {row[0]: row[1] for row in result}

    async def soft_delete_variety(self, ticker: str) -> bool:
        """软删除品种"""
        async with async_session() as session:
            record = (await session.execute(
                select(AssetVarietyRecord).where(
                    AssetVarietyRecord.ticker == ticker,
                    AssetVarietyRecord.is_active == True,
                )
            )).scalar_one_or_none()
            if not record:
                return False
            record.is_active = False
            await session.commit()
            return True


def _record_to_variety(r: AssetVarietyRecord) -> AssetVariety:
    return AssetVariety(
        ticker=r.ticker,
        name=r.name,
        market=r.market,
        asset_class=r.asset_class,
        sub_category=r.sub_category,
        currency=r.currency,
        is_active=r.is_active,
    )
