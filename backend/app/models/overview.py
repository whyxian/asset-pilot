"""概览统计 Pydantic 模型"""

from decimal import Decimal

from pydantic import BaseModel


class AllocationItem(BaseModel):
    """资产配比单项"""
    market: str       # "CN" / "US" / "CRYPTO"
    label: str        # 显示名
    value_cny: Decimal
    pct: float        # 百分比


class OverviewStats(BaseModel):
    """概览统计（所有金额统一为 CNY）"""
    total_value_cny: Decimal = Decimal("0")
    total_cost_cny: Decimal = Decimal("0")
    total_pnl_cny: Decimal = Decimal("0")
    total_pnl_pct: float | None = None
    annualized_return: float | None = None
    allocation: list[AllocationItem] = []
