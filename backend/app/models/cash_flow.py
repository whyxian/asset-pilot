"""资金流水 Pydantic 模型 — cash_flows"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CashFlow(BaseModel):
    """资金流水 — 响应"""
    id: int
    type: str  # deposit / withdraw / buy / sell
    amount: Decimal  # 正=入账，负=出账
    currency: str
    transaction_id: int | None = None
    notes: str | None = None
    created_at: datetime | None = None


class CashBalance(BaseModel):
    """币种余额 — 响应"""
    currency: str
    balance: Decimal = Decimal("0")


class CashBalancesResponse(BaseModel):
    """现金余额聚合 - 按显示币种换算后的总额 + 各币种明细"""
    display_currency: str                       # 显示币种（如 CNY）
    total: Decimal = Decimal("0")               # 所有币种余额换算到 display_currency 的总和
    balances: list[CashBalance] = []            # 各币种原始余额
    rate_source_date: str | None = None         # 汇率日期
    rate_stale: bool = False                    # 汇率是否走了兜底


class CashDepositCreate(BaseModel):
    """入金请求"""
    amount: Decimal = Field(..., gt=0, description="入金金额，正数")
    currency: str = Field(default="USD", max_length=3)
    notes: str | None = None


class CashWithdrawCreate(BaseModel):
    """出金请求"""
    amount: Decimal = Field(..., gt=0, description="出金金额，正数（系统内部存为负）")
    currency: str = Field(default="USD", max_length=3)
    notes: str | None = None
