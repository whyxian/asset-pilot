from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class QuoteStatus(str, Enum):
    """行情获取状态 — 供前端区分实时/降级/不可用"""
    REALTIME = "REALTIME"          # 实时行情（数据源刚拉的）
    HISTORICAL = "HISTORICAL"      # DB 历史兜底（实时失败，回查 DB 最新一条）
    UNAVAILABLE = "UNAVAILABLE"    # 连历史都没有（现价 0，建仓后从未成功落库的极端情况）


class AssetQuote(BaseModel):
    """归一化后的资产报价"""
    ticker: str                       # 标的代码, 如 "600519" / "AAPL" / "bitcoin"
    asset_class: str = ""             # 资产类别, "STOCK" / "FUND" / "CRYPTO"（由 service 层在 fetch 后统一打上）
    market: str                       # 市场, "CN" / "US" / "CRYPTO"
    name: str = ""                    # 名称, 如 "贵州茅台" / "Apple Inc"
    price: Decimal                    # 最新价
    currency: str = "USD"             # 计价货币, CNY / USD
    change_price: Optional[Decimal] = None  # 涨跌额
    change_ratio: Optional[float] = None  # 涨跌幅（百分比）
    updated_at: datetime = Field(default_factory=datetime.now)  # 数据时间戳
    source: str = ""                  # 数据来源, "AKSHARE" / "YAHOO" / "COINGECKO"
