"""TransactionRecord ORM 模型 — 对应 transactions 表"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TransactionRecord(Base):
    """交易记录表 — 每笔买入/卖出操作

    (asset_class, market, ticker) 三元组对应 asset_holdings 中唯一一笔持仓。
    """

    __tablename__ = "transactions"
    __table_args__ = (
        # 复合索引便于按品种回放交易（recompute_holding 频繁使用）
        Index("ix_txn_class_market_ticker", "asset_class", "market", "ticker"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(10), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(4), nullable=False)  # "buy" / "sell"
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
