"""持仓数据访问 — asset_holdings 表 CRUD"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def get_record_in_session(
        self, session: AsyncSession, ticker: str
    ) -> AssetHoldingRecord | None:
        """在外部 session 内获取 ORM 记录（供事务内重算使用）"""
        return (await session.execute(
            select(AssetHoldingRecord).where(AssetHoldingRecord.ticker == ticker)
        )).scalar_one_or_none()

    async def create_holding(self, data: AssetHoldingCreate) -> AssetHolding:
        """新增持仓 — 同时把请求的 quantity/cost_price/total_invested 写入 initial_* 作为建仓基线"""
        record = AssetHoldingRecord(
            ticker=data.ticker,
            name=data.name,
            market=data.market,
            asset_class=data.asset_class,
            currency=data.currency,
            quantity=data.quantity,
            cost_price=data.cost_price,
            total_invested=data.total_invested,
            # 建仓基线 = 此次新建时填入的状态
            initial_quantity=data.quantity,
            initial_cost_price=data.cost_price,
            initial_total_invested=data.total_invested,
            first_buy_date=data.first_buy_date,
        )
        async with async_session() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return _record_to_holding(record)

    async def update_holding(self, ticker: str, data: AssetHoldingUpdate) -> AssetHolding | None:
        """更新持仓 — quantity/cost_price/total_invested 同步写到 initial_* 作为新基线

        语义：用户在持仓页手动修改持仓，相当于重设建仓基线。
        调用方需在 update 后触发该 ticker 的全量重算（_recompute_holding），
        以使派生字段反映"新基线 + 现有交易回放"的结果。
        """
        async with async_session() as session:
            record = (await session.execute(
                select(AssetHoldingRecord).where(AssetHoldingRecord.ticker == ticker)
            )).scalar_one_or_none()
            if not record:
                return None

            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if value is None:
                    continue
                setattr(record, key, value)
                # 同步基线列
                if key == "quantity":
                    record.initial_quantity = value
                elif key == "cost_price":
                    record.initial_cost_price = value
                elif key == "total_invested":
                    record.initial_total_invested = value
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
