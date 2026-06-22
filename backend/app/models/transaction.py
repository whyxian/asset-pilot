"""交易记录 Pydantic 模型"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """交易记录 — 响应模型"""

    id: int
    ticker: str
    asset_class: str        # STOCK / FUND / CRYPTO
    market: str             # CN / US / CRYPTO
    transaction_date: date
    type: str  # "buy" / "sell"
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    fee_rate: Decimal | None = None  # 费率百分比（如 0.03 表示万分之三）
    notes: str | None = None


class TransactionCreate(BaseModel):
    """新增交易记录 — 请求体"""

    ticker: str
    asset_class: str
    market: str
    transaction_date: date
    type: str = Field(..., pattern=r"^(buy|sell)$")  # 只允许 buy / sell
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    fee_rate: Decimal | None = None
    notes: str | None = None


class TransactionUpdate(BaseModel):
    """更新交易记录 — 请求体（所有字段可选）"""

    ticker: str | None = None
    asset_class: str | None = None
    market: str | None = None
    transaction_date: date | None = None
    type: str | None = Field(None, pattern=r"^(buy|sell)$")
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    fee_rate: Decimal | None = None
    notes: str | None = None
