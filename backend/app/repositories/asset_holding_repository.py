"""持仓数据访问 — asset_holdings 表 CRUD"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.asset_holding import AssetHolding, AssetHoldingCreate, AssetHoldingUpdate
from app.models.orm.asset_holding_orm import AssetHoldingRecord


class AssetHoldingRepository:
    """持仓数据访问

    业务约束：(asset_class, market, ticker) 三元组在 asset_holdings 中唯一。
    所有按品种定位的查询都必须传完整三元组。
    """

    async def list_holdings(self) -> list[AssetHolding]:
        """获取全部持仓"""
        async with async_session() as session:
            records = (await session.execute(
                select(AssetHoldingRecord).order_by(AssetHoldingRecord.ticker)
            )).scalars().all()
            return [_record_to_holding(r) for r in records]

    async def get_holding(
        self, ticker: str, asset_class: str, market: str
    ) -> AssetHolding | None:
        """按三元组获取持仓"""
        async with async_session() as session:
            r = (await session.execute(
                select(AssetHoldingRecord).where(
                    AssetHoldingRecord.ticker == ticker,
                    AssetHoldingRecord.asset_class == asset_class,
                    AssetHoldingRecord.market == market,
                )
            )).scalar_one_or_none()
            return _record_to_holding(r) if r else None

    async def get_record_in_session(
        self, session: AsyncSession, ticker: str, asset_class: str, market: str
    ) -> AssetHoldingRecord | None:
        """在外部 session 内获取 ORM 记录（供事务内重算使用）"""
        return (await session.execute(
            select(AssetHoldingRecord).where(
                AssetHoldingRecord.ticker == ticker,
                AssetHoldingRecord.asset_class == asset_class,
                AssetHoldingRecord.market == market,
            )
        )).scalar_one_or_none()

    async def create_holding(self, data: AssetHoldingCreate) -> AssetHolding:
        """新增持仓 — initial_* 已废弃，派生字段由 recompute_holding 从交易回放算出"""
        record = AssetHoldingRecord(
            ticker=data.ticker,
            name=data.name,
            market=data.market,
            asset_class=data.asset_class,
            currency=data.currency,
            quantity=data.quantity,
            cost_price=data.cost_price,
            total_invested=data.total_invested,
            first_buy_date=data.first_buy_date,
        )
        async with async_session() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return _record_to_holding(record)

    async def update_holding(
        self, ticker: str, asset_class: str, market: str, data: AssetHoldingUpdate
    ) -> AssetHolding | None:
        """更新持仓 — 仅更新非现金流字段（name 等）。

        quantity/cost_price/total_invested 的修改由 service 层生成勘误交易 + recompute 处理，
        不在此直接改派生字段。first_buy_date 由建仓交易决定，不允许改。
        """
        async with async_session() as session:
            record = (await session.execute(
                select(AssetHoldingRecord).where(
                    AssetHoldingRecord.ticker == ticker,
                    AssetHoldingRecord.asset_class == asset_class,
                    AssetHoldingRecord.market == market,
                )
            )).scalar_one_or_none()
            if not record:
                return None

            update_data = data.model_dump(exclude_unset=True)
            # 仅更新 name 等非现金流字段；quantity/cost_price/total_invested/first_buy_date
            # 由 service 层通过勘误交易 + recompute 处理，不在此直接改
            for key in ("name",):
                if key in update_data and update_data[key] is not None:
                    setattr(record, key, update_data[key])
            await session.commit()
            await session.refresh(record)
            return _record_to_holding(record)

    async def delete_holding(
        self, ticker: str, asset_class: str, market: str
    ) -> bool:
        """删除持仓（仅 ORM 删除一行；不级联删交易，调用方负责）"""
        async with async_session() as session:
            record = (await session.execute(
                select(AssetHoldingRecord).where(
                    AssetHoldingRecord.ticker == ticker,
                    AssetHoldingRecord.asset_class == asset_class,
                    AssetHoldingRecord.market == market,
                )
            )).scalar_one_or_none()
            if not record:
                return False
            await session.delete(record)
            await session.commit()
            return True

    async def list_all_tickers(self) -> dict[tuple[str, str], list[str]]:
        """查询所有活跃持仓的 ticker，按 (asset_class, market) 分组

        供定时任务拉取行情使用。去重，已清仓的品种不参与。
        """
        from collections import defaultdict
        async with async_session() as session:
            rows = (await session.execute(
                select(
                    AssetHoldingRecord.asset_class,
                    AssetHoldingRecord.market,
                    AssetHoldingRecord.ticker,
                ).where(AssetHoldingRecord.liquidated_at.is_(None))
            )).all()
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for ac, market, ticker in rows:
            if ticker not in groups[(ac, market)]:
                groups[(ac, market)].append(ticker)
        return dict(groups)


def _record_to_holding(r: AssetHoldingRecord) -> AssetHolding:
    """ORM 记录转 Pydantic 模型"""
    return AssetHolding(
        ticker=r.ticker,
        name=r.name,
        market=r.market,
        asset_class=r.asset_class,
        currency=r.currency,
        quantity=Decimal(str(r.quantity)),
        cost_price=Decimal(str(r.cost_price)),
        total_invested=Decimal(str(r.total_invested)),
        first_buy_date=r.first_buy_date if isinstance(r.first_buy_date, date) else r.first_buy_date.date(),
        liquidated_at=(
            r.liquidated_at if r.liquidated_at is None or isinstance(r.liquidated_at, date)
            else r.liquidated_at.date()
        ),
    )
