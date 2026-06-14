"""AssetQuote ORM 模型 — 对应 asset_quote 表"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Float, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssetQuoteRecord(Base):
    """资产报价记录表

    业务约束：(asset_class, market, ticker) 三元组才能唯一定位品种
    （A 股 000001 vs 基金 000001 ticker 重合），所以行情快照按
    (asset_class, market, ticker, timestamp) 四元组去重。
    """

    __tablename__ = "asset_quote"
    __table_args__ = (
        UniqueConstraint(
            "asset_class", "market", "ticker", "timestamp",
            name="uq_quote_class_market_ticker_ts",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(10), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="")
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    change_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    change_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
