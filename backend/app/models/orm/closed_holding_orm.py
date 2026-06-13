"""归档持仓 ORM — closed_holdings + closed_transactions

业务语义：
- closed_holdings：每完成一个持仓周期（建仓 → 卖光）就在此插入一行
- closed_transactions：归档时把该周期内的全部 transactions 复制到这里，原表删除
- ticker 在 closed_holdings 不唯一（可被归档多次：买 → 清 → 又买 → 又清）
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClosedHoldingRecord(Base):
    """归档持仓 — 一笔已完成的持仓周期"""

    __tablename__ = "closed_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(10), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")

    # 建仓时的基线快照（不变量）
    initial_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    initial_cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    initial_total_invested: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    first_buy_date: Mapped[date] = mapped_column(Date, nullable=False)
    closed_at: Mapped[date] = mapped_column(Date, nullable=False)
    holding_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # 该周期总实现盈亏 = sum(sell.amount) - sum(buy.amount) - initial_total_invested
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)


class ClosedTransactionRecord(Base):
    """归档交易记录 — 关联到某个 closed_holding"""

    __tablename__ = "closed_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    closed_holding_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("closed_holdings.id"), nullable=False, index=True
    )
    # 字段镜像 transactions 表
    ticker: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 追溯：原 transactions.id（归档后原表已删除，但保留 id 以备审计）
    original_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
