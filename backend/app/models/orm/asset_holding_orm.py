"""AssetHolding ORM 模型 — 对应 asset_holdings 表"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssetHoldingRecord(Base):
    """当前持仓记录表"""

    __tablename__ = "asset_holdings"
    __table_args__ = (
        # 同一品种(三元组)只允许一行；同 ticker 不同 market/asset_class 可共存
        # （例：A 股 000001=平安银行 与 基金 000001=华夏成长 可同时持有）
        UniqueConstraint("asset_class", "market", "ticker", name="uq_holding_class_market_ticker"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(10), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_invested: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    # 建仓基线：建仓时填入的初始状态，不随交易自动变化
    # 派生字段（quantity / cost_price / total_invested）= initial_* + 全部 transactions 回放
    initial_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    initial_cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    initial_total_invested: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    first_buy_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    # 清仓日期：quantity 回到 0 时由 recompute_holding 写入最后一笔 sell 的日期，
    # 后续若复活（再次 buy）则清空。NULL 表示从未清仓或建仓时即为 0
    liquidated_at: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
