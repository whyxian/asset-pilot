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
