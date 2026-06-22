"""概览统计 Pydantic 模型

base 设计：
- 字段名不带币种后缀（不再叫 total_value_cny）
- currency 字段说明当前数据所在币种
- 后端聚合用 USD，按 ?currency=CNY 参数换算返回
"""

from decimal import Decimal

from pydantic import BaseModel


class AllocationItem(BaseModel):
    """资产配比单项"""
    market: str       # "CN" / "US" / "CRYPTO"
    label: str        # 显示名
    value: Decimal    # 该市场总市值（按当前 currency）
    pct: float        # 百分比


class OverviewStats(BaseModel):
    """概览统计

    所有金额按 currency 字段标识的币种返回。
    """
    currency: str = "USD"             # 当前数据所在币种
    total_value: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    total_pnl: Decimal = Decimal("0")
    total_pnl_pct: float | str | None = None      # 零成本时为 "+∞%"
    annualized_return: float | str | None = None  # 零成本时为 "+∞%"
    cumulative_return: Decimal = Decimal("0")      # 历史累计收益金额（Modified Dietz）
    allocation: list[AllocationItem] = []
    rate_source_date: str | None = None  # 当前所用汇率的日期（前端展示）
    rate_stale: bool = False             # 汇率是否走了兜底（旧汇率，前端警告）
