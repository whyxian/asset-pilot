"""AssetHolding Pydantic 模型 — 持仓"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class AssetHolding(BaseModel):
    """当前持仓"""
    ticker: str                       # 标的代码
    name: str = ""                    # 名称
    market: str                       # 市场, "CN" / "US" / "CRYPTO"
    asset_class: str                  # 资产类别, "STOCK" / "FUND"
    currency: str = "CNY"             # 计价货币
    quantity: Decimal                 # 持仓量
    cost_price: Decimal               # 加权平均成本价
    total_invested: Decimal           # 总投入金额
    first_buy_date: date              # 首次买入日期
    first_buy_price: Decimal = Decimal("0")  # 建仓首笔买入价（盈亏率分母）
    liquidated_at: Optional[date] = None  # 清仓日期，未清仓为 None


class AssetHoldingCreate(BaseModel):
    """新增持仓请求"""
    ticker: str
    name: str = ""
    market: str
    asset_class: str
    currency: str = "CNY"
    quantity: Decimal
    cost_price: Decimal
    total_invested: Decimal
    first_buy_date: date


class AssetHoldingUpdate(BaseModel):
    """更新持仓请求"""
    name: Optional[str] = None
    quantity: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    total_invested: Optional[Decimal] = None
    first_buy_date: Optional[date] = None


class HoldingWithQuote(BaseModel):
    """持仓 + 实时行情"""
    ticker: str
    name: str
    market: str
    asset_class: str
    currency: str
    quantity: Decimal
    cost_price: Decimal
    total_invested: Decimal
    first_buy_date: date
    first_buy_price: Decimal = Decimal("0")  # 建仓首笔买入价
    liquidated_at: Optional[date] = None  # 清仓日期，未清仓为 None
    # 以下为实时计算字段
    current_price: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")
    pnl: Decimal = Decimal("0")
    pnl_pct: float | str | None = None       # 零成本时为 "∞"
    annualized_return: float | str | None = None  # 零成本时为 "∞"
    quote_status: str = "REALTIME"           # 行情状态：REALTIME / HISTORICAL / UNAVAILABLE


class MarketSummary(BaseModel):
    """单市场汇总——供持仓页展示市场占比"""
    market: str                          # "CN" / "US" / "CRYPTO"
    label: str                           # 显示名，如 "A 股"
    count: int                           # 该市场持仓品种数
    value_usd: Decimal = Decimal("0")    # 该市场总市值（USD，用于跨币种聚合算占比）
    pct: float = 0.0                     # 占组合总市值百分比


class HoldingsWithQuotesResponse(BaseModel):
    """持仓列表 + 市场汇总（with-quotes 接口返回结构）"""
    holdings: list[HoldingWithQuote] = []
    market_summary: list[MarketSummary] = []
