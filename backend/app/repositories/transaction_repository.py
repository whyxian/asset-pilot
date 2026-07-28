"""交易记录数据访问 - transactions 表 CRUD"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.core.database import async_session
from app.models.common import PaginatedResponse
from app.models.orm.transaction_orm import TransactionRecord
from app.models.transaction import Transaction, TransactionCreate, TransactionUpdate


class TransactionRepository:
    """交易记录数据访问"""

    async def list_transactions(
        self,
        ticker: str | None = None,
        asset_class: str | None = None,
        market: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[Transaction]:
        """获取交易记录列表（按日期倒序，分页）

        三个筛选都是可选；任一非空就加 where 条件。要按持仓精确筛选时三个一起传。
        """
        async with async_session() as session:
            base = select(TransactionRecord)
            count_stmt = select(func.count()).select_from(TransactionRecord)
            if ticker:
                base = base.where(TransactionRecord.ticker == ticker)
                count_stmt = count_stmt.where(TransactionRecord.ticker == ticker)
            if asset_class:
                base = base.where(TransactionRecord.asset_class == asset_class)
                count_stmt = count_stmt.where(TransactionRecord.asset_class == asset_class)
            if market:
                base = base.where(TransactionRecord.market == market)
                count_stmt = count_stmt.where(TransactionRecord.market == market)

            total = (await session.execute(count_stmt)).scalar() or 0
            records = (await session.execute(
                base.order_by(TransactionRecord.transaction_date.desc(), TransactionRecord.id.desc())
                .limit(page_size).offset((page - 1) * page_size)
            )).scalars().all()
            return PaginatedResponse[Transaction](
                data=[_record_to_transaction(r) for r in records],
                total=total, page=page, page_size=page_size,
            )

    async def get_transaction(self, transaction_id: int) -> Transaction | None:
        """按 ID 获取单条交易记录"""
        async with async_session() as session:
            r = (await session.execute(
                select(TransactionRecord).where(TransactionRecord.id == transaction_id)
            )).scalar_one_or_none()
            return _record_to_transaction(r) if r else None

    async def create_transaction(self, data: TransactionCreate) -> Transaction:
        """新增交易记录"""
        record = TransactionRecord(
            ticker=data.ticker,
            asset_class=data.asset_class,
            market=data.market,
            transaction_date=data.transaction_date,
            type=data.type,
            quantity=data.quantity if data.quantity is not None else None,
            unit_price=data.unit_price if data.unit_price is not None else None,
            amount=data.amount if data.amount is not None else None,
            fee_rate=data.fee_rate if data.fee_rate is not None else None,
            notes=data.notes,
        )
        async with async_session() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return _record_to_transaction(record)

    async def update_transaction(
        self, transaction_id: int, data: TransactionUpdate
    ) -> Transaction | None:
        """更新交易记录"""
        async with async_session() as session:
            record = (await session.execute(
                select(TransactionRecord).where(TransactionRecord.id == transaction_id)
            )).scalar_one_or_none()
            if not record:
                return None

            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if value is not None:
                    setattr(record, key, value)
            await session.commit()
            await session.refresh(record)
            return _record_to_transaction(record)

    async def delete_transaction(self, transaction_id: int) -> bool:
        """删除交易记录"""
        async with async_session() as session:
            record = (await session.execute(
                select(TransactionRecord).where(TransactionRecord.id == transaction_id)
            )).scalar_one_or_none()
            if not record:
                return False
            await session.delete(record)
            await session.commit()
            return True


def _record_to_transaction(r: TransactionRecord) -> Transaction:
    """ORM 记录转 Pydantic 模型"""
    return Transaction(
        id=r.id,
        ticker=r.ticker,
        asset_class=r.asset_class,
        market=r.market,
        transaction_date=r.transaction_date if isinstance(r.transaction_date, date) else r.transaction_date.date(),
        type=r.type,
        quantity=Decimal(str(r.quantity)) if r.quantity is not None else None,
        unit_price=Decimal(str(r.unit_price)) if r.unit_price is not None else None,
        amount=Decimal(str(r.amount)) if r.amount is not None else None,
        fee_rate=Decimal(str(r.fee_rate)) if r.fee_rate is not None else None,
        notes=r.notes,
    )
