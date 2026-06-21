"""归档持仓 Pydantic 模型"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ClosedTransaction(BaseModel):
    """归档交易记录 — 响应"""
    id: int
    closed_holding_id: int
    ticker: str
    asset_class: str
    market: str
    transaction_date: date
    type: str  # "buy" / "sell"
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    notes: Optional[str] = None
    original_id: Optional[int] = None


class ClosedHolding(BaseModel):
    """归档持仓 — 响应"""
    id: int
    ticker: str
    name: str
    market: str
    asset_class: str
    currency: str
    total_buy_amount: Decimal             # 该周期总买入金额（sum(buy.amount)）
    first_buy_date: date
    first_buy_price: Decimal = Decimal("0")  # 建仓首笔买入价
    closed_at: date
    holding_days: int
    realized_pnl: Decimal


class ClosedHoldingDetail(ClosedHolding):
    """归档持仓详情 — 含该周期全部交易"""
    transactions: list[ClosedTransaction] = []
