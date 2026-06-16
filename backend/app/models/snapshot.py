"""快照 Pydantic 模型 — 净值快照 + 资产快照"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.overview import AllocationItem


class NetWorthSnapshot(BaseModel):
    """组合级净值快照（按 currency 字段标识的币种返回）"""
    snapshot_date: date
    currency: str = "USD"
    total_value: Decimal
    total_cost: Decimal
    total_pnl: Decimal
    total_pnl_pct: float | str | None = None
    annualized_return: float | str | None = None
    allocation: list[AllocationItem] = []


class AssetSnapshot(BaseModel):
    """品种级日快照（金额按 currency 字段标识的币种返回）

    Note:
        - unit_value / cost_value / market_value / unrealized_pnl 始终是原币
          （这些字段表达"那一刻该品种的价格状态"，原币才有意义）
        - market_value_in_currency / total_invested_in_currency 是按目标币种换算的值，
          用来在前端做组合级展示
    """
    snapshot_date: date
    ticker: str
    asset_class: str
    market: str
    name: str = ""
    currency: str  # 该品种的原币

    quantity: Decimal
    unit_value: Decimal
    cost_value: Decimal
    market_value: Decimal
    total_invested: Decimal
    unrealized_pnl: Decimal
    return_pct: float | None = None

    # 按目标显示币种换算后的值（用快照里冻结的 fx_rates 算）
    display_currency: str = "USD"
    market_value_in_currency: Decimal = Decimal("0")
    total_invested_in_currency: Decimal = Decimal("0")
