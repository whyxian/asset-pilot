"""汇率工具 — 从 GitHub 源获取实时汇率，缓存 1 小时"""

import time
from decimal import Decimal

import httpx

from app.core.logger import logger

_RATES_URL = "https://raw.githubusercontent.com/Sunny-DotNet/ExchangeRates/main/mini.json"
_CACHE_TTL = 3600  # 缓存 1 小时（数据源每小时更新）

_cache: dict = {"rates": None, "fetched_at": 0}


async def fetch_rates() -> dict[str, float] | None:
    """获取实时汇率（USD 为基准），带内存缓存

    Returns:
        { "CNY": 6.7767, "EUR": 0.8672, ... } 或 None
    """
    now = time.time()
    if _cache["rates"] and (now - _cache["fetched_at"]) < _CACHE_TTL:
        return _cache["rates"]

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(_RATES_URL)
            data = resp.json()
        rates = data.get("datas")
        if not rates:
            raise ValueError("缺少 datas 字段")
        _cache["rates"] = rates
        _cache["fetched_at"] = now
        logger.info(f"汇率已更新 ({data.get('date', '?')})")
        return rates
    except Exception as e:
        logger.error(f"获取汇率失败: {e}")
        # 缓存未过期则继续用旧数据
        return _cache["rates"]


async def to_cny(amount: Decimal, from_currency: str) -> Decimal:
    """将金额从指定货币换算为 CNY

    Args:
        amount: 原始金额
        from_currency: 原始货币代码，如 "USD" / "CNY" / "HKD"

    Returns:
        换算后的 CNY 金额
    """
    if from_currency == "CNY":
        return amount

    rates = await fetch_rates()
    if not rates:
        logger.warning(f"汇率数据不可用，{from_currency}→CNY 换算失败，返回原值")
        return amount

    cny_rate = rates.get("CNY")
    src_rate = rates.get(from_currency)
    if not cny_rate or not src_rate:
        logger.warning(f"缺少汇率: CNY={cny_rate}, {from_currency}={src_rate}")
        return amount

    # 源金额 → USD（除以源汇率）→ CNY（乘以 CNY 汇率）
    usd_amount = amount / Decimal(str(src_rate))
    return usd_amount * Decimal(str(cny_rate))
