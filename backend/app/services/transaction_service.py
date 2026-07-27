"""交易记录业务逻辑

业务约束：transactions 表通过 (asset_class, market, ticker) 三元组关联到 holdings 中
唯一一笔持仓。所有按品种操作都必须传完整三元组。
"""

from sqlalchemy import delete, func, select

from decimal import Decimal

from app.core.database import async_session
from app.core.exceptions import BusinessError
from app.models.orm.asset_holding_orm import AssetHoldingRecord
from app.models.orm.cash_flow_orm import CashFlowRecord
from app.models.orm.transaction_orm import TransactionRecord
from app.models.transaction import Transaction, TransactionCreate, TransactionUpdate
from app.repositories.transaction_repository import TransactionRepository
from app.services.asset_holding_service import archive_holding, recompute_holding


class TransactionService:
    """交易记录业务逻辑"""

    def __init__(self):
        self._repo = TransactionRepository()

    async def list_transactions(
        self,
        ticker: str | None = None,
        asset_class: str | None = None,
        market: str | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        """获取交易记录列表（按日期倒序）；三个筛选都是可选"""
        return await self._repo.list_transactions(
            ticker=ticker, asset_class=asset_class, market=market, limit=limit
        )

    async def get_transaction(self, transaction_id: int) -> Transaction | None:
        """获取单条交易记录"""
        return await self._repo.get_transaction(transaction_id)

    async def create_transaction(self, data: TransactionCreate) -> Transaction:
        """新增交易记录（事务内：写入 + 重算持仓 + 必要时归档，原子操作）

        校验链：
        1. (quantity + unit_price) 或 amount 至少一组
        2. 必须先建仓 — 持仓表中必须已存在 (asset_class, market, ticker) 三元组
        3. fee_rate 范围 0~100
        4. amount 与 qty × price × (1 + fee_rate/100) 一致（不一致则拒绝）
        """
        await self._validate_create_payload(data)

        async with async_session() as session:
            try:
                record = TransactionRecord(
                    ticker=data.ticker,
                    asset_class=data.asset_class,
                    market=data.market,
                    transaction_date=data.transaction_date,
                    type=data.type,
                    quantity=data.quantity,
                    unit_price=data.unit_price,
                    amount=data.amount,
                    fee_rate=data.fee_rate,
                    notes=data.notes,
                )
                session.add(record)
                await session.flush()  # 让 INSERT 落到当前事务，便于重算时 SELECT 到

                # 在同一事务内回放重算持仓
                await recompute_holding(session, data.ticker, data.asset_class, data.market)

                # 现金账户联动：先查持仓现金开关（归档前，holding 还在）
                holding_cash = (await session.execute(
                    select(AssetHoldingRecord).where(
                        AssetHoldingRecord.ticker == data.ticker,
                        AssetHoldingRecord.asset_class == data.asset_class,
                        AssetHoldingRecord.market == data.market,
                    )
                )).scalar_one_or_none()
                if holding_cash is not None and holding_cash.cash_account_enabled and record.amount is not None:
                    txn_amt = Decimal(str(record.amount))
                    if data.type == "buy":
                        balance = await self._get_cash_balance(session, holding_cash.currency)
                        if balance < txn_amt:
                            raise BusinessError(40001,
                                f"{holding_cash.currency} 现金余额不足：当前 {balance}，需要 {txn_amt}")
                        session.add(CashFlowRecord(
                            type="buy", amount=-txn_amt, currency=holding_cash.currency,
                            transaction_id=record.id,
                            notes=f"买入 {data.ticker} 扣款" if data.notes is None else data.notes,
                        ))
                    elif data.type == "sell":
                        session.add(CashFlowRecord(
                            type="sell", amount=txn_amt, currency=holding_cash.currency,
                            transaction_id=record.id,
                            notes=f"卖出 {data.ticker} 入账" if data.notes is None else data.notes,
                        ))

                # 提前快照（归档会删除 record，refresh 会失败）
                snapshot = _orm_to_transaction(record)

                # 如果重算后持仓为 0，立即归档
                await self._archive_if_zero(session, data.ticker, data.asset_class, data.market)

                await session.commit()
                return snapshot
            except Exception:
                await session.rollback()
                raise

    async def _archive_if_zero(
        self, session, ticker: str, asset_class: str, market: str
    ) -> None:
        """重算后如果该品种持仓为 0，触发归档"""
        from decimal import Decimal as _D
        holding = (await session.execute(
            select(AssetHoldingRecord).where(
                AssetHoldingRecord.ticker == ticker,
                AssetHoldingRecord.asset_class == asset_class,
                AssetHoldingRecord.market == market,
            )
        )).scalar_one_or_none()
        if holding is not None and _D(str(holding.quantity)) == _D("0"):
            await archive_holding(session, ticker, asset_class, market)

    async def update_transaction(
        self, transaction_id: int, data: TransactionUpdate
    ) -> Transaction | None:
        """更新交易记录（事务内：写入 + 重算受影响品种，原子操作）

        如果修改了三元组（ticker / asset_class / market 任一），需要重算
        新旧两个品种（旧的少了这笔，新的多了这笔）。

        校验：fee_rate 范围 + amount 一致性（用合并后的完整数据验算）
        """
        from decimal import Decimal as _D

        async with async_session() as session:
            try:
                record = (await session.execute(
                    select(TransactionRecord).where(TransactionRecord.id == transaction_id)
                )).scalar_one_or_none()
                if not record:
                    return None

                # 合并新旧值，用于验算
                merged_qty = data.quantity if data.quantity is not None else record.quantity
                merged_price = data.unit_price if data.unit_price is not None else record.unit_price
                merged_amount = data.amount if data.amount is not None else record.amount
                merged_fee = data.fee_rate if data.fee_rate is not None else record.fee_rate

                # fee_rate 范围校验
                if merged_fee is not None and (merged_fee < 0 or merged_fee > 100):
                    raise BusinessError(40001, f"费率必须在 0~100 之间，当前值 {merged_fee}")

                # amount 一致性验算
                if merged_qty is not None and merged_price is not None and merged_amount is not None:
                    qty = _D(str(merged_qty))
                    price = _D(str(merged_price))
                    fee = _D(str(merged_fee)) if merged_fee is not None else _D("0")
                    expected = qty * price * (_D("1") + fee / _D("100"))
                    actual = _D(str(merged_amount))
                    if abs(expected - actual) > _D("0.01"):
                        raise BusinessError(
                            40001,
                            f"交易金额与 数量×成交价×(1+费率%) 不一致：期望 {expected}，实际 {actual}",
                        )

                record = (await session.execute(
                    select(TransactionRecord).where(TransactionRecord.id == transaction_id)
                )).scalar_one_or_none()
                if not record:
                    return None

                # 旧三元组（用于回算）
                old_triple = (record.ticker, record.asset_class, record.market)

                # 新三元组：data 里有就替换，没传则保留原值
                new_ticker = data.ticker if data.ticker is not None else record.ticker
                new_class = data.asset_class if data.asset_class is not None else record.asset_class
                new_market = data.market if data.market is not None else record.market
                new_triple = (new_ticker, new_class, new_market)

                # 改三元组时，新品种也必须有持仓基线
                if new_triple != old_triple:
                    holding = (await session.execute(
                        select(AssetHoldingRecord).where(
                            AssetHoldingRecord.ticker == new_ticker,
                            AssetHoldingRecord.asset_class == new_class,
                            AssetHoldingRecord.market == new_market,
                        )
                    )).scalar_one_or_none()
                    if not holding:
                        raise BusinessError(
                            40001,
                            f"请先在持仓页新增 {new_ticker} ({new_class}/{new_market}) 的建仓记录，再录入交易",
                        )

                # 应用更新
                update_data = data.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(record, key, value)
                await session.flush()

                # 重算：新旧三元组都要算
                triples_to_recompute = {old_triple, new_triple}
                for t, ac, mk in triples_to_recompute:
                    await recompute_holding(session, t, ac, mk)

                # 提前快照（归档会删除 record）
                snapshot = _orm_to_transaction(record)

                # 任一品种持仓为 0 都要归档
                for t, ac, mk in triples_to_recompute:
                    await self._archive_if_zero(session, t, ac, mk)

                # 现金账户联动：同步更新 cash_flow amount
                if data.amount is not None and record.amount is not None and str(record.amount) != str(data.amount):
                    holding = (await session.execute(
                        select(AssetHoldingRecord).where(
                            AssetHoldingRecord.ticker == new_ticker,
                            AssetHoldingRecord.asset_class == new_class,
                            AssetHoldingRecord.market == new_market,
                        )
                    )).scalar_one_or_none()
                    if holding is not None and holding.cash_account_enabled:
                        cf = (await session.execute(
                            select(CashFlowRecord).where(
                                CashFlowRecord.transaction_id == record.id
                            )
                        )).scalar_one_or_none()
                        if cf is not None and data.amount is not None:
                            new_amt = _D(str(data.amount))
                            cf.amount = -new_amt if record.type == "buy" else new_amt
                            await session.flush()

                await session.commit()
                return snapshot
            except Exception:
                await session.rollback()
                raise

    async def delete_transaction(self, transaction_id: int) -> bool:
        """删除交易记录（事务内：删除 + 重算原品种，原子操作）"""
        async with async_session() as session:
            try:
                record = (await session.execute(
                    select(TransactionRecord).where(TransactionRecord.id == transaction_id)
                )).scalar_one_or_none()
                if not record:
                    return False

                ticker = record.ticker
                asset_class = record.asset_class
                market = record.market
                # 现金账户联动：先删关联 cash_flow（回退现金）
                await session.execute(
                    delete(CashFlowRecord).where(CashFlowRecord.transaction_id == transaction_id)
                )
                await session.delete(record)
                await session.flush()

                # 重算原品种（少了这笔交易）— 注意：可能恰好让持仓为 0 触发归档
                await recompute_holding(session, ticker, asset_class, market)
                await self._archive_if_zero(session, ticker, asset_class, market)

                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    async def _get_cash_balance(self, session, currency: str) -> Decimal:
        """查指定币种的现金余额（事务内）"""
        from sqlalchemy import func, select
        result = (await session.execute(
            select(func.coalesce(func.sum(CashFlowRecord.amount), 0))
            .where(CashFlowRecord.currency == currency)
        )).scalar()
        return Decimal(str(result))

    async def _validate_create_payload(self, data: TransactionCreate) -> None:
        """create 的前置业务校验：字段组合 / 必须先建仓 / fee_rate 范围 / amount 一致性"""
        from decimal import Decimal as _D

        # 至少填 quantity+unit_price 或 amount 之一
        has_qty_price = data.quantity is not None and data.unit_price is not None
        has_amount = data.amount is not None
        if not has_qty_price and not has_amount:
            raise BusinessError(
                40001,
                "请填写 (数量 + 成交价) 或 (交易金额)，至少填一组",
            )

        # fee_rate 范围校验：0~100
        if data.fee_rate is not None:
            if data.fee_rate < 0 or data.fee_rate > 100:
                raise BusinessError(40001, f"费率必须在 0~100 之间，当前值 {data.fee_rate}")

        # amount 一致性验算：qty × price × (1 + fee_rate/100) 必须与传入的 amount 一致
        if has_qty_price and has_amount:
            qty = _D(str(data.quantity))
            price = _D(str(data.unit_price))
            fee = _D(str(data.fee_rate)) if data.fee_rate is not None else _D("0")
            expected = qty * price * (_D("1") + fee / _D("100"))
            actual = _D(str(data.amount))
            # 允许 0.01 的精度误差（Decimal 除法尾差）
            if abs(expected - actual) > _D("0.01"):
                raise BusinessError(
                    40001,
                    f"交易金额与 数量×成交价×(1+费率%) 不一致：期望 {expected}，实际 {actual}",
                )

        # 必须先建仓（按三元组定位）
        async with async_session() as session:
            holding = (await session.execute(
                select(AssetHoldingRecord).where(
                    AssetHoldingRecord.ticker == data.ticker,
                    AssetHoldingRecord.asset_class == data.asset_class,
                    AssetHoldingRecord.market == data.market,
                )
            )).scalar_one_or_none()
            if not holding:
                raise BusinessError(
                    40001,
                    f"请先在持仓页新增 {data.ticker} ({data.asset_class}/{data.market}) 的建仓记录，再录入交易",
                )


def _orm_to_transaction(r: TransactionRecord) -> Transaction:
    """ORM 记录转 Pydantic 模型（与 transaction_repository 内部函数等价）"""
    from datetime import date as date_type
    from decimal import Decimal
    return Transaction(
        id=r.id,
        ticker=r.ticker,
        asset_class=r.asset_class,
        market=r.market,
        transaction_date=r.transaction_date if isinstance(r.transaction_date, date_type) else r.transaction_date.date(),
        type=r.type,
        quantity=Decimal(str(r.quantity)) if r.quantity is not None else None,
        unit_price=Decimal(str(r.unit_price)) if r.unit_price is not None else None,
        amount=Decimal(str(r.amount)) if r.amount is not None else None,
        fee_rate=Decimal(str(r.fee_rate)) if r.fee_rate is not None else None,
        notes=r.notes,
    )
