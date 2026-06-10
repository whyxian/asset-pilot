"""AssetHolding ORM 模型 — 对应 asset_holdings 表"""

from datetime import datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssetHoldingRecord(Base):
    """当前持仓记录表"""

    __tablename__ = "asset_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(30), nullable=False, index=True, unique=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(10), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    cost_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    total_invested: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    first_buy_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
