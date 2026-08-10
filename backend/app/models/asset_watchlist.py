"""Watchlist Pydantic 模型 — 自选股"""

from pydantic import BaseModel, Field

from app.models.asset_quote import AssetQuote, QuoteStatus


class WatchlistItem(BaseModel):
    """自选股条目"""
    id: int
    ticker: str
    asset_class: str
    market: str
    name: str


class WatchlistWithQuote(BaseModel):
    """自选条目 + 实时行情（三态）"""
    id: int
    ticker: str
    asset_class: str
    market: str
    name: str
    quote: AssetQuote | None = None
    status: QuoteStatus = QuoteStatus.UNAVAILABLE


class WatchlistCreate(BaseModel):
    """收藏请求"""
    ticker: str = Field(..., max_length=30)
    asset_class: str = Field(..., max_length=10)
    market: str = Field(..., max_length=10)
    name: str = Field(default="", max_length=200)
