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

    async def get_variety(self, ticker: str) -> AssetVariety | None:
        """按代码查询品种"""
        async with async_session() as session:
            r = (await session.execute(
                select(AssetVarietyRecord).where(
                    AssetVarietyRecord.ticker == ticker,
                    AssetVarietyRecord.is_active == True,
                )
            )).scalar_one_or_none()
            return _record_to_variety(r) if r else None

    async def create_variety(self, data: AssetVarietyCreate) -> AssetVariety:
        """新增品种"""
        record = AssetVarietyRecord(
            ticker=data.ticker,
            name=data.name,
            market=data.market,
            asset_class=data.asset_class,
            currency=data.currency,
        )
        async with async_session() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return _record_to_variety(record)

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
        currency=r.currency,
        is_active=r.is_active,
    )
