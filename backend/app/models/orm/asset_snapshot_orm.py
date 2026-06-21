"""品种级快照 ORM — asset_snapshots 表

每天每只持仓一条，冻结当下的状态（持仓量、行情、成本、盈亏）。
同时存原币和 USD 值：原币便于审计；USD 便于聚合和未来跨币种回溯。
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssetSnapshotRecord(Base):
    """品种级日快照"""

    __tablename__ = "asset_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "asset_class", "market", "ticker", "snapshot_date",
            name="uq_asset_snap_class_market_ticker_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    ticker: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(10), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="")
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)      # 现价（原币）
    cost_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)      # 成本价（原币）
    first_buy_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))  # 建仓首笔买入价（原币）
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)    # 市值（原币）
    market_value_usd: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)  # 市值（USD）
    total_invested: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)      # 总投入（原币）
    total_invested_usd: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)  # 总投入（USD）
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)  # 浮动盈亏（原币）
    return_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
