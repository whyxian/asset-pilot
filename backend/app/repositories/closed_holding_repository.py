"""归档持仓数据访问 — closed_holdings + closed_transactions

只读 repository（归档动作由 asset_holding_service.archive_holding 完成）。
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.database import async_session
from app.models.closed_holding import ClosedHolding, ClosedHoldingDetail, ClosedTransaction
from app.models.orm.closed_holding_orm import ClosedHoldingRecord, ClosedTransactionRecord


class ClosedHoldingRepository:
    """归档持仓数据访问"""

    async def list_closed_holdings(self) -> list[ClosedHolding]:
        """获取全部归档持仓（按清仓日倒序）"""
        async with async_session() as session:
            records = (await session.execute(
                select(ClosedHoldingRecord).order_by(
                    ClosedHoldingRecord.closed_at.desc(),
                    ClosedHoldingRecord.id.desc(),
                )
            )).scalars().all()
            return [_record_to_closed_holding(r) for r in records]

    async def get_closed_holding(self, holding_id: int) -> ClosedHoldingDetail | None:
        """获取单条归档持仓详情（含全部关联交易）"""
        async with async_session() as session:
            r = (await session.execute(
                select(ClosedHoldingRecord).where(ClosedHoldingRecord.id == holding_id)
            )).scalar_one_or_none()
            if not r:
                return None

            txn_records = (await session.execute(
                select(ClosedTransactionRecord)
                .where(ClosedTransactionRecord.closed_holding_id == holding_id)
                .order_by(
                    ClosedTransactionRecord.transaction_date.asc(),
                    ClosedTransactionRecord.id.asc(),
                )
            )).scalars().all()

            return ClosedHoldingDetail(
                **_record_to_closed_holding(r).model_dump(),
                transactions=[_record_to_closed_transaction(t) for t in txn_records],
            )

    async def list_closed_transactions(self, limit: int = 500) -> list[ClosedTransaction]:
        """获取全部归档交易（按交易日倒序，便于"近期归档先看到"）"""
        async with async_session() as session:
            records = (await session.execute(
                select(ClosedTransactionRecord)
                .order_by(
                    ClosedTransactionRecord.transaction_date.desc(),
                    ClosedTransactionRecord.id.desc(),
                )
                .limit(limit)
            )).scalars().all()
            return [_record_to_closed_transaction(r) for r in records]


def _record_to_closed_holding(r: ClosedHoldingRecord) -> ClosedHolding:
    return ClosedHolding(
        id=r.id,
        ticker=r.ticker,
        name=r.name,
        market=r.market,
        asset_class=r.asset_class,
        currency=r.currency,
        initial_quantity=Decimal(str(r.initial_quantity)),
        initial_cost_price=Decimal(str(r.initial_cost_price)),
        initial_total_invested=Decimal(str(r.initial_total_invested)),
        first_buy_date=r.first_buy_date if isinstance(r.first_buy_date, date) else r.first_buy_date.date(),
        closed_at=r.closed_at if isinstance(r.closed_at, date) else r.closed_at.date(),
        holding_days=r.holding_days,
        realized_pnl=Decimal(str(r.realized_pnl)),
    )


def _record_to_closed_transaction(r: ClosedTransactionRecord) -> ClosedTransaction:
    return ClosedTransaction(
        id=r.id,
        closed_holding_id=r.closed_holding_id,
        ticker=r.ticker,
        transaction_date=r.transaction_date if isinstance(r.transaction_date, date) else r.transaction_date.date(),
        type=r.type,
        quantity=Decimal(str(r.quantity)) if r.quantity is not None else None,
        unit_price=Decimal(str(r.unit_price)) if r.unit_price is not None else None,
        amount=Decimal(str(r.amount)) if r.amount is not None else None,
        notes=r.notes,
        original_id=r.original_id,
    )
