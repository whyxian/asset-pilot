"""归档持仓数据访问 — closed_holdings + closed_transactions

只读 repository（归档动作由 asset_holding_service.archive_holding 完成）。
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.core.database import async_session
from app.models.closed_holding import ClosedHolding, ClosedHoldingDetail, ClosedTransaction
from app.models.common import PaginatedResponse
from app.models.orm.closed_holding_orm import ClosedHoldingRecord, ClosedTransactionRecord


class ClosedHoldingRepository:
    """归档持仓数据访问"""

    async def list_closed_holdings(self, page: int = 1, page_size: int = 20) -> PaginatedResponse[ClosedHolding]:
        """获取全部归档持仓（按清仓日倒序，分页）"""
        async with async_session() as session:
            total = (await session.execute(
                select(func.count()).select_from(ClosedHoldingRecord)
            )).scalar() or 0
            records = (await session.execute(
                select(ClosedHoldingRecord).order_by(
                    ClosedHoldingRecord.closed_at.desc(),
                    ClosedHoldingRecord.id.desc(),
                ).limit(page_size).offset((page - 1) * page_size)
            )).scalars().all()
            return PaginatedResponse[ClosedHolding](
                data=[_record_to_closed_holding(r) for r in records],
                total=total, page=page, page_size=page_size,
            )

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

    async def list_closed_transactions(self, page: int = 1, page_size: int = 20) -> PaginatedResponse[ClosedTransaction]:
        """获取全部归档交易（按交易日倒序，分页）"""
        async with async_session() as session:
            total = (await session.execute(
                select(func.count()).select_from(ClosedTransactionRecord)
            )).scalar() or 0
            records = (await session.execute(
                select(ClosedTransactionRecord)
                .order_by(
                    ClosedTransactionRecord.transaction_date.desc(),
                    ClosedTransactionRecord.id.desc(),
                )
                .limit(page_size).offset((page - 1) * page_size)
            )).scalars().all()
            return PaginatedResponse[ClosedTransaction](
                data=[_record_to_closed_transaction(r) for r in records],
                total=total, page=page, page_size=page_size,
            )


    async def delete_closed_holding(self, holding_id: int) -> bool:
        """删除归档持仓及其关联交易，返回是否删除成功"""
        async with async_session() as session:
            r = (await session.execute(
                select(ClosedHoldingRecord).where(ClosedHoldingRecord.id == holding_id)
            )).scalar_one_or_none()
            if not r:
                return False
            # 先删关联交易（FK 约束）
            await session.execute(
                ClosedTransactionRecord.__table__.delete()
                .where(ClosedTransactionRecord.closed_holding_id == holding_id)
            )
            await session.delete(r)
            await session.commit()
            return True


def _record_to_closed_holding(r: ClosedHoldingRecord) -> ClosedHolding:
    return ClosedHolding(
        id=r.id,
        ticker=r.ticker,
        name=r.name,
        market=r.market,
        asset_class=r.asset_class,
        currency=r.currency,
        total_buy_amount=Decimal(str(r.total_buy_amount)),
        first_buy_date=r.first_buy_date if isinstance(r.first_buy_date, date) else r.first_buy_date.date(),
        first_buy_price=Decimal(str(r.first_buy_price)),
        closed_at=r.closed_at if isinstance(r.closed_at, date) else r.closed_at.date(),
        holding_days=r.holding_days,
        realized_pnl=Decimal(str(r.realized_pnl)),
        pnl_pct=float(r.pnl_pct) if r.pnl_pct is not None else None,
        is_crazy_trader=bool(r.is_crazy_trader),
    )


def _record_to_closed_transaction(r: ClosedTransactionRecord) -> ClosedTransaction:
    return ClosedTransaction(
        id=r.id,
        closed_holding_id=r.closed_holding_id,
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
        original_id=r.original_id,
    )
