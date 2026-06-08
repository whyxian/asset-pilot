"""AssetVariety Pydantic 模型 — 品种目录"""

from typing import Optional

from pydantic import BaseModel


class AssetVariety(BaseModel):
    """资产品种"""
    ticker: str
    name: str
    market: str      # A / US / CRYPTO
    asset_class: str # STOCK / FUND
    currency: str    # CNY / USD
    is_active: bool = True


class AssetVarietyCreate(BaseModel):
    """新增品种请求"""
    ticker: str
    name: str
    market: str
    asset_class: str
    currency: str = "CNY"
