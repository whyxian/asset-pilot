"""交易记录业务逻辑"""

from sqlalchemy import select

from app.core.database import async_session
from app.core.exceptions import BusinessError
from app.models.orm.asset_holding_orm import AssetHoldingRecord
from app.models.orm.transaction_orm import TransactionRecord
from app.models.transaction import Transaction, TransactionCreate, TransactionUpdate
from app.repositories.asset_variety_repository import AssetVarietyRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.asset_holding_service import recompute_holding


class TransactionService:
    """交易记录业务逻辑"""

    def __init__(self):
        self._repo = TransactionRepository()
        self._variety_repo = AssetVarietyRepository()

    async def list_transactions(
        self, ticker: str | None = None, limit: int = 100
    ) -> list[Transaction]:
        """获取交易记录列表"""
        return await self._repo.list_transactions(ticker=ticker, limit=limit)

    async def get_transaction(self, transaction_id: int) -> Transaction | None:
        """获取单条交易记录"""
        return await self._repo.get_transaction(transaction_id)

    async def create_transaction(self, data: TransactionCreate) -> Transaction:
        """新增交易记录（事务内：写入 + 重算持仓，原子操作）

        校验链：
        1. 品种存在性
        2. (quantity + unit_price) 或 amount 至少一组
        3. 必须先建仓 — 持仓表中必须已存在该 ticker
        """
        await self._validate_create_payload(data)

        async with async_session() as session:
            try:
                record = TransactionRecord(
                    ticker=data.ticker,
                    transaction_date=data.transaction_date,
                    type=data.type,
                    quantity=data.quantity,
                    unit_price=data.unit_price,
                    amount=data.amount,
                    notes=data.notes,
                )
                session.add(record)
                await session.flush()  # 让 INSERT 落到当前事务，便于重算时 SELECT 到

                # 在同一事务内回放重算持仓
                await recompute_holding(session, data.ticker)

                await session.commit()
                await session.refresh(record)
                return _orm_to_transaction(record)
            except Exception:
                await session.rollback()
                raise

    async def update_transaction(
        self, transaction_id: int, data: TransactionUpdate
    ) -> Transaction | None:
        """更新交易记录（事务内：写入 + 重算受影响 ticker，原子操作）

        如果修改了 ticker，需要重算新旧两个 ticker（旧 ticker 少了这笔，新 ticker 多了这笔）。
        """
        async with async_session() as session:
            try:
                record = (await session.execute(
                    select(TransactionRecord).where(TransactionRecord.id == transaction_id)
                )).scalar_one_or_none()
                if not record:
                    return None

                old_ticker = record.ticker
                new_ticker = data.ticker if data.ticker is not None else old_ticker

                # 改 ticker 时，新 ticker 也必须有持仓基线
                if new_ticker != old_ticker:
                    holding = (await session.execute(
                        select(AssetHoldingRecord).where(AssetHoldingRecord.ticker == new_ticker)
                    )).scalar_one_or_none()
                    if not holding:
                        raise BusinessError(
                            40001,
                            f"请先在持仓页新增 {new_ticker} 的建仓记录，再录入交易",
                        )

                # 应用更新
                update_data = data.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(record, key, value)
                await session.flush()

                # 重算：先旧后新（如果 ticker 改了，两个都要算）
                tickers_to_recompute = {old_ticker, new_ticker}
                for t in tickers_to_recompute:
                    await recompute_holding(session, t)

                await session.commit()
                await session.refresh(record)
                return _orm_to_transaction(record)
            except Exception:
                await session.rollback()
                raise

    async def delete_transaction(self, transaction_id: int) -> bool:
        """删除交易记录（事务内：删除 + 重算原 ticker，原子操作）"""
        async with async_session() as session:
            try:
                record = (await session.execute(
                    select(TransactionRecord).where(TransactionRecord.id == transaction_id)
                )).scalar_one_or_none()
                if not record:
                    return False

                ticker = record.ticker
                await session.delete(record)
                await session.flush()

                # 重算原 ticker（少了这笔交易）
                await recompute_holding(session, ticker)

                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    async def _validate_create_payload(self, data: TransactionCreate) -> None:
        """create 的前置业务校验：品种存在 / 字段组合 / 必须先建仓"""
        # 校验品种是否存在
        variety = await self._variety_repo.get_variety(data.ticker)
        if not variety:
            raise BusinessError(40001, f"未识别的品种代码 '{data.ticker}'，请先通过 /api/v1/varieties 添加该品种")

        # 至少填 quantity+unit_price 或 amount 之一
        has_qty_price = data.quantity is not None and data.unit_price is not None
        has_amount = data.amount is not None
        if not has_qty_price and not has_amount:
            raise BusinessError(
                40001,
                "请填写 (数量 + 成交价) 或 (交易金额)，至少填一组",
            )

        # 必须先建仓
        async with async_session() as session:
            holding = (await session.execute(
                select(AssetHoldingRecord).where(AssetHoldingRecord.ticker == data.ticker)
            )).scalar_one_or_none()
            if not holding:
                raise BusinessError(
                    40001,
                    f"请先在持仓页新增 {data.ticker} 的建仓记录，再录入交易",
                )


def _orm_to_transaction(r: TransactionRecord) -> Transaction:
    """ORM 记录转 Pydantic 模型（与 transaction_repository 内部函数等价，避免在 service 层反向引用 repo 内部函数）"""
    from datetime import date as date_type
    from decimal import Decimal
    return Transaction(
        id=r.id,
        ticker=r.ticker,
        transaction_date=r.transaction_date if isinstance(r.transaction_date, date_type) else r.transaction_date.date(),
        type=r.type,
        quantity=Decimal(str(r.quantity)) if r.quantity is not None else None,
        unit_price=Decimal(str(r.unit_price)) if r.unit_price is not None else None,
        amount=Decimal(str(r.amount)) if r.amount is not None else None,
        notes=r.notes,
    )
