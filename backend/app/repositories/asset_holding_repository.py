"""持仓数据访问 — asset_holdings 表 CRUD"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.database import async_session
from app.models.asset_holding import AssetHolding, AssetHoldingCreate, AssetHoldingUpdate
from app.models.orm.asset_holding_orm import AssetHoldingRecord


class AssetHoldingRepository:
    """持仓数据访问"""

    async def list_holdings(self) -> list[AssetHolding]:
        """获取全部持仓"""
        async with async_session() as session:
            records = (await session.execute(
                select(AssetHoldingRecord).order_by(AssetHoldingRecord.ticker)
            )).scalars().all()
            return [_record_to_holding(r) for r in records]

    async def get_holding(self, ticker: str) -> AssetHolding | None:
        """按代码获取持仓"""
        async with async_session() as session:
            r = (await session.execute(
                select(AssetHoldingRecord).where(AssetHoldingRecord.ticker == ticker)
            )).scalar_one_or_none()
            return _record_to_holding(r) if r else None

    async def create_holding(self, data: AssetHoldingCreate) -> AssetHolding:
        """新增持仓"""
        record = AssetHoldingRecord(
            ticker=data.ticker,
            name=data.name,
            market=data.market,
            asset_class=data.asset_class,
            currency=data.currency,
            quantity=float(data.quantity),
            cost_price=float(data.cost_price),
            total_invested=float(data.total_invested),
            first_buy_date=data.first_buy_date,
        )
        async with async_session() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return _record_to_holding(record)

    async def update_holding(self, ticker: str, data: AssetHoldingUpdate) -> AssetHolding | None:
        """更新持仓"""
        async with async_session() as session:
            record = (await session.execute(
                select(AssetHoldingRecord).where(AssetHoldingRecord.ticker == ticker)
            )).scalar_one_or_none()
            if not record:
                return None

            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if value is not None:
                    setattr(record, key, float(value) if key in ("quantity", "cost_price", "total_invested") else value)
            await session.commit()
            await session.refresh(record)
            return _record_to_holding(record)

    async def delete_holding(self, ticker: str) -> bool:
        """删除持仓"""
        async with async_session() as session:
            record = (await session.execute(
                select(AssetHoldingRecord).where(AssetHoldingRecord.ticker == ticker)
            )).scalar_one_or_none()
            if not record:
                return False
            await session.delete(record)
            await session.commit()
            return True


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
    )
