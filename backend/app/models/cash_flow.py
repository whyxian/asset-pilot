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
