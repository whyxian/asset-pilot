"""组合级净值快照 ORM — networth_snapshots 表

每天一条，是 asset_snapshots 在该日的预聚合（物化视图）。
存储以 USD 为基准，配合 fx_rates 字段冻结当日汇率，
查询时按目标币种用快照里的汇率换算 — 历史曲线反映"那一刻"的币种价值。
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NetWorthSnapshotRecord(Base):
    """组合级净值快照"""

    __tablename__ = "networth_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)

    total_value_usd: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_pnl_usd: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    annualized_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)

    # JSON: [{market, label, value_usd, pct}]
    allocation: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # JSON: 快照时的汇率 {"CNY": 7.2, "HKD": 7.81, ...}（USD 为 1.0）
    fx_rates: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
