"""自选股数据访问 — watchlist 表 CRUD"""

from sqlalchemy import select

from app.core.database import async_session
from app.models.asset_watchlist import WatchlistCreate, WatchlistItem
from app.models.orm.asset_watchlist_orm import WatchlistRecord


class WatchlistRepository:
    """自选股数据访问"""

    async def list_watchlist(self) -> list[WatchlistItem]:
        """获取全部自选（sort_order 升序 + 收藏时间倒序）"""
        async with async_session() as session:
            records = (await session.execute(
                select(WatchlistRecord)
                .order_by(WatchlistRecord.sort_order, WatchlistRecord.id.desc())
            )).scalars().all()
            return [_record_to_item(r) for r in records]

    async def get_watchlist(
        self, ticker: str, asset_class: str, market: str
    ) -> WatchlistItem | None:
        """按三元组查询自选（幂等判断用）"""
        async with async_session() as session:
            r = (await session.execute(
                select(WatchlistRecord).where(
                    WatchlistRecord.ticker == ticker,
                    WatchlistRecord.asset_class == asset_class,
                    WatchlistRecord.market == market,
                )
            )).scalar_one_or_none()
            return _record_to_item(r) if r else None

    async def create_watchlist(self, data: WatchlistCreate) -> WatchlistItem:
        """新增自选"""
        record = WatchlistRecord(
            ticker=data.ticker,
            asset_class=data.asset_class,
            market=data.market,
            name=data.name,
        )
        async with async_session() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return _record_to_item(record)

    async def delete_watchlist(self, watchlist_id: int) -> bool:
        """取消收藏（幂等：不存在返回 False）"""
        async with async_session() as session:
            record = (await session.execute(
                select(WatchlistRecord).where(WatchlistRecord.id == watchlist_id)
            )).scalar_one_or_none()
            if not record:
                return False
            await session.delete(record)
            await session.commit()
            return True


def _record_to_item(r: WatchlistRecord) -> WatchlistItem:
    return WatchlistItem(
        id=r.id,
        ticker=r.ticker,
        asset_class=r.asset_class,
        market=r.market,
        name=r.name,
    )
