"""汇率工具 — 从 GitHub 源获取实时汇率，缓存 1 小时

设计要点：
- 汇率数据源以 USD 为基准（rates["CNY"] = 7.2 表示 1 USD = 7.2 CNY）
- 内部以 USD 为枢轴：所有换算先 → USD → 目标币种
- to_cny() 保留作为兼容 wrapper（多处旧代码在用）
"""

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
        { "CNY": 7.2, "EUR": 0.92, "HKD": 7.8, ... } 或 None
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


async def fetch_rates_snapshot() -> dict[str, float]:
    """快照场景：拿当前汇率快照，无可用汇率时抛错

    Returns:
        完整 rates dict，可冻结到快照里

    Raises:
        RuntimeError: 网络失败且无缓存可用
    """
    rates = await fetch_rates()
    if not rates:
        raise RuntimeError("无法获取汇率，且本地缓存为空，无法记录快照")
    return dict(rates)  # 拷贝一份避免外部改动影响缓存


def convert_with_rates(
    amount: Decimal, from_ccy: str, to_ccy: str, rates: dict
) -> Decimal:
    """同步换算：用传入的 rates dict（不调网络）

    用于历史快照换算 — 用快照时冻结的汇率，不用当前汇率。

    Args:
        amount: 原始金额
        from_ccy: 原币
        to_ccy: 目标币种
        rates: USD-base rates dict，如 {"CNY": 7.2, "USD": 1.0, ...}

    Returns:
        换算后金额；汇率缺失时返回原值并记日志（避免历史数据查询失败）
    """
    if from_ccy == to_ccy:
        return amount
    # USD 在 rates 里通常显式为 1.0，但也兜底
    if from_ccy == "USD":
        rate = rates.get(to_ccy)
        if not rate:
            logger.warning(f"汇率缺失: {to_ccy}，返回原值")
            return amount
        return amount * Decimal(str(rate))
    if to_ccy == "USD":
        rate = rates.get(from_ccy)
        if not rate:
            logger.warning(f"汇率缺失: {from_ccy}，返回原值")
            return amount
        return amount / Decimal(str(rate))
    # 跨非 USD：原币 → USD → 目标币种
    src_rate = rates.get(from_ccy)
    dst_rate = rates.get(to_ccy)
    if not src_rate or not dst_rate:
        logger.warning(f"汇率缺失: {from_ccy}={src_rate} {to_ccy}={dst_rate}，返回原值")
        return amount
    return amount / Decimal(str(src_rate)) * Decimal(str(dst_rate))


async def convert(amount: Decimal, from_ccy: str, to_ccy: str) -> Decimal:
    """通用换算：原币 → USD → 目标币种（用当前汇率）"""
    if from_ccy == to_ccy:
        return amount
    rates = await fetch_rates()
    if not rates:
        logger.warning(f"汇率不可用，{from_ccy}→{to_ccy} 换算失败，返回原值")
        return amount
    return convert_with_rates(amount, from_ccy, to_ccy, rates)


async def to_usd(amount: Decimal, from_currency: str) -> Decimal:
    """原币 → USD"""
    return await convert(amount, from_currency, "USD")


async def from_usd(amount: Decimal, to_currency: str) -> Decimal:
    """USD → 目标币种"""
    return await convert(amount, "USD", to_currency)


async def to_cny(amount: Decimal, from_currency: str) -> Decimal:
    """原币 → CNY（保留兼容旧调用）"""
    return await convert(amount, from_currency, "CNY")
