"""资金流水数据访问 — cash_flows"""

from decimal import Decimal

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.cash_flow import CashBalance, CashFlow
from app.models.common import PaginatedResponse
from app.models.orm.cash_flow_orm import CashFlowRecord


class CashFlowRepository:
    """资金流水数据访问"""

    async def create_flow(
        self, type_: str, amount: Decimal, currency: str,
        transaction_id: int | None = None, notes: str | None = None,
        session: AsyncSession | None = None,
    ) -> CashFlow:
        """创建资金流水记录"""
        async with session or async_session() as s:
            record = CashFlowRecord(
                type=type_, amount=amount, currency=currency,
                transaction_id=transaction_id, notes=notes,
            )
            s.add(record)
            if not session:
                await s.commit()
                await s.refresh(record)
            else:
                await s.flush()
            return CashFlow(
                id=record.id, type=record.type, amount=amount,
                currency=currency, transaction_id=transaction_id,
                notes=notes,
            )

    async def list_flows(self, page: int = 1, page_size: int = 20) -> PaginatedResponse[CashFlow]:
        """流水列表（按创建时间倒序，分页）"""
        async with async_session() as session:
            total = (await session.execute(
                select(func.count()).select_from(CashFlowRecord)
            )).scalar() or 0
            records = (await session.execute(
                select(CashFlowRecord)
                .order_by(CashFlowRecord.created_at.desc(), CashFlowRecord.id.desc())
                .limit(page_size).offset((page - 1) * page_size)
            )).scalars().all()
            return PaginatedResponse[CashFlow](
                data=[_record_to_flow(r) for r in records],
                total=total, page=page, page_size=page_size,
            )

    async def get_balances(self) -> list[CashBalance]:
        """按币种汇总余额"""
        async with async_session() as session:
            rows = (await session.execute(
                select(CashFlowRecord.currency, func.sum(CashFlowRecord.amount).label("balance"))
                .group_by(CashFlowRecord.currency)
            )).all()
            return [CashBalance(currency=row[0], balance=Decimal(str(row[1]))) for row in rows]

    async def delete_flow(self, flow_id: int) -> bool:
        """删除资金流水"""
        async with async_session() as session:
            result = await session.execute(
                delete(CashFlowRecord).where(CashFlowRecord.id == flow_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def delete_by_transaction(self, txn_id: int, session: AsyncSession | None = None) -> None:
        """根据关联交易 ID 删除流水（事务内）"""
        async with session or async_session() as s:
            await s.execute(
                delete(CashFlowRecord).where(CashFlowRecord.transaction_id == txn_id)
            )
            if not session:
                await s.commit()

    async def get_by_transaction(self, txn_id: int) -> CashFlow | None:
        """按交易 ID 查流水"""
        async with async_session() as session:
            r = (await session.execute(
                select(CashFlowRecord).where(CashFlowRecord.transaction_id == txn_id)
            )).scalar_one_or_none()
            return _record_to_flow(r) if r else None


def _record_to_flow(r: CashFlowRecord) -> CashFlow:
    return CashFlow(
        id=r.id, type=r.type, amount=r.amount,
        currency=r.currency, transaction_id=r.transaction_id,
        notes=r.notes, created_at=r.created_at,
    )
