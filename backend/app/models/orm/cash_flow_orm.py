"""资金流水 ORM — cash_flows

业务语义：
- 独立于 transactions 表，记录所有资金进出
- deposit: 外部资金注入（正）
- withdraw: 资金取出（负）
- buy: 买入持仓扣款（负，关联 transaction_id）
- sell: 卖出持仓入账（正，关联 transaction_id）
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CashFlowRecord(Base):
    """资金流水 — 单笔资金变动"""

    __tablename__ = "cash_flows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # deposit / withdraw / buy / sell
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)  # 正=入账，负=出账
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # buy/sell 时关联 transactions.id；deposit/withdraw 时为 NULL
    transaction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("transactions.id"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
