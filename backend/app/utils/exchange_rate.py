"""汇率工具 — 从 GitHub 源获取实时汇率，缓存 1 小时

设计要点：
- 汇率数据源以 USD 为基准（rates["CNY"] = 7.2 表示 1 USD = 7.2 CNY）
- 内部以 USD 为枢轴：所有换算先 → USD → 目标币种
- to_cny() 保留作为兼容 wrapper（多处旧代码在用）
- 五级兜底：内存新鲜值（1h TTL）→ 内存过期旧值 → 运行时磁盘缓存 → 种子文件 → 硬编码常量
  网络失败时按此链路回退，保证全新环境 + 断网 + 种子被删也有兜底，永不返回 None
"""

import asyncio
import json
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import httpx

from app.core.logger import logger


@dataclass
class RatesSnapshot:
    """汇率快照——含所用汇率的日期与新鲜度，供上层透传给前端展示

    is_stale=True 表示网络失败走了兜底（内存过期/磁盘/种子/硬编码），
    此时 source_date 可能是几天前的旧日期，前端应警告提示。
    """
    rates: dict[str, float]
    source_date: str | None
    is_stale: bool

_RATES_URL = "https://raw.githubusercontent.com/Sunny-DotNet/ExchangeRates/main/mini.json"
_CACHE_TTL = 3600  # 内存缓存 1 小时（数据源每小时更新），过期后触发重拉但旧值仍可兜底
_FETCH_TIMEOUT = 5  # 网络超时秒数——五级兜底充足，不必久等，失败立刻走兜底

# 单飞：N 个并发请求同时触发 fetch_rates 时，只发 1 个网络请求，其余等结果复用
# 避免概览 60s 轮询 + 前端重试叠加时发 N 个慢请求各自卡满超时
_inflight: asyncio.Task | None = None

# 运行时磁盘缓存（gitignore，运行时成功拉取后覆盖更新）
_PERSIST_PATH = Path(__file__).resolve().parents[3] / "data" / "exchange_rates_cache.json"
# 种子兜底文件（提交进仓库，全新环境/容器无持久卷 + 断网时的兜底）
_FALLBACK_PATH = Path(__file__).resolve().parents[3] / "data" / "dbjson" / "exchange_rates_fallback.json"

# 硬编码兜底汇率（USD 为基准，2026-06-18 快照）——种子文件也被删时的终极兜底
# 与 data/dbjson/exchange_rates_fallback.json 同源；汇率漂移后两处一起手动更新
_HARDCODED_RATES: dict[str, float] = {
    'AED': 3.6725,
    'AFN': 63.499997,
    'ALL': 82.68742,
    'AMD': 368.611858,
    'ANG': 1.79,
    'AOA': 913.116,
    'ARS': 1448.2544,
    'AUD': 1.421393,
    'AWG': 1.8,
    'AZN': 1.7,
    'BAM': 1.687031,
    'BBD': 2,
    'BDT': 122.802043,
    'BGN': 1.703531,
    'BHD': 0.377256,
    'BIF': 2983.04907,
    'BMD': 1,
    'BND': 1.283781,
    'BOB': 6.913076,
    'BRL': 5.1781,
    'BSD': 1,
    'BTN': 94.317204,
    'BWP': 13.4484,
    'BYN': 2.769718,
    'BZD': 2.012037,
    'CAD': 1.41199,
    'CDF': 2308.742138,
    'CHF': 0.802299,
    'CLP': 891.86,
    'CNY': 6.7585,
    'COP': 3480.97,
    'CRC': 454.321821,
    'CUP': 25.75,
    'CVE': 95.112192,
    'CZK': 21.0584,
    'DJF': 178.151432,
    'DKK': 6.50724,
    'DOP': 58.621996,
    'DZD': 133.459019,
    'EGP': 49.9198,
    'ERN': 15,
    'ETB': 158.25357,
    'EUR': 0.870619,
    'FJD': 2.2218,
    'FKP': 0.754616,
    'GBP': 0.754616,
    'GEL': 2.645,
    'GHS': 11.204846,
    'GIP': 0.754616,
    'GMD': 73.000001,
    'GNF': 8764.568372,
    'GTQ': 7.624493,
    'GYD': 209.303889,
    'HKD': 7.83764,
    'HNL': 26.756978,
    'HTG': 130.782806,
    'HUF': 306.598153,
    'IDR': 17811.014278,
    'ILS': 2.939985,
    'INR': 94.222248,
    'IQD': 1310.6156,
    'IRR': 1375000,
    'ISK': 125.55,
    'JMD': 158.464288,
    'JOD': 0.709,
    'JPY': 160.8595,
    'KES': 129.45,
    'KGS': 87.45,
    'KHR': 4025.63739,
    'KMF': 424.999927,
    'KPW': 900,
    'KRW': 1534.167968,
    'KWD': 0.307897,
    'KYD': 0.833672,
    'KZT': 488.416933,
    'LAK': 22052.014514,
    'LBP': 89576.533135,
    'LKR': 333.681027,
    'LRD': 182.07925,
    'LYD': 6.382487,
    'MAD': 9.319332,
    'MDL': 17.512482,
    'MGA': 4176.600251,
    'MKD': 53.683414,
    'MMK': 2099.81,
    'MNT': 3569.47,
    'MOP': 8.076114,
    'MRU': 39.916379,
    'MUR': 47.499996,
    'MVR': 15.46,
    'MWK': 1734.730457,
    'MXN': 17.351461,
    'MYR': 4.1179,
    'MZN': 63.899993,
    'NAD': 16.222581,
    'NGN': 1361.19,
    'NIO': 36.817048,
    'NOK': 9.699083,
    'NPR': 150.908218,
    'NZD': 1.731482,
    'OMR': 0.384489,
    'PAB': 1,
    'PEN': 3.390083,
    'PGK': 4.382665,
    'PHP': 60.452001,
    'PKR': 278.282329,
    'PLN': 3.706626,
    'PYG': 6118.26795,
    'QAR': 3.646886,
    'RON': 4.5616,
    'RSD': 102.195,
    'RUB': 73.326281,
    'RWF': 1465.540491,
    'SAR': 3.754595,
    'SBD': 8.061424,
    'SCR': 13.34533,
    'SDG': 600.5,
    'SEK': 9.541505,
    'SGD': 1.288602,
    'SHP': 0.754616,
    'SOS': 571.727266,
    'SRD': 37.385,
    'SSP': 130.26,
    'STN': 21.13326,
    'SYP': 13002,
    'SZL': 16.226684,
    'THB': 32.7355,
    'TJS': 9.283859,
    'TMT': 3.51,
    'TND': 2.944455,
    'TOP': 2.40776,
    'TRY': 46.444337,
    'TTD': 6.793553,
    'TWD': 31.577115,
    'TZS': 2630.488,
    'UAH': 44.897373,
    'UGX': 3651.188042,
    'USD': 1,
    'UYU': 40.351412,
    'UZS': 12059.004168,
    'VES': 596.036846,
    'VND': 26326.181844,
    'VUV': 119.389,
    'WST': 2.74422,
    'XAF': 571.088491,
    'XCD': 2.70255,
    'XOF': 571.088491,
    'XPF': 103.892457,
    'YER': 238.625037,
    'ZAR': 16.401,
    'ZMW': 17.894567,
}
_HARDCODED_SOURCE_DATE = "2026-06-18"

# 内存 L1 缓存：{rates, fetched_at, source_date, is_stale}
_cache: dict = {"rates": None, "fetched_at": 0, "source_date": None, "is_stale": False}


def _load_persisted() -> tuple[dict[str, float], str | None] | None:
    """从磁盘读取兜底汇率：优先运行时缓存（较新），没有则读种子文件（较旧但永在）

    进程重启后首次网络失败时调用，保证全新环境也有兜底。
    返回 (rates, source_date)，source_date 取文件里的 date 字段。
    """
    for path in (_PERSIST_PATH, _FALLBACK_PATH):
        try:
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                # 兼容两种格式：运行时缓存 {rates: {...}} / 数据源原始 {datas: {...}}
                # 用 is not None 判断，避免空 dict {} 被当作 falsy 错误回退到 datas
                rates = payload.get("rates")
                if rates is None:
                    rates = payload.get("datas")
                if rates:
                    source_date = payload.get("source_date") or payload.get("date")
                    if path == _FALLBACK_PATH:
                        logger.warning(f"使用种子汇率兜底 ({source_date or '?'})")
                    return rates, source_date
        except Exception as e:
            logger.warning(f"读取汇率兜底文件失败 {path.name}: {e}")
    return None


def _persist(rates: dict[str, float], source_date: str | None) -> None:
    """把成功拉取的汇率落盘（覆盖写，作为后续重启兜底）"""
    try:
        _PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PERSIST_PATH.write_text(
            json.dumps(
                {"rates": rates, "source_date": source_date, "fetched_at": time.time()},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"写入磁盘汇率兜底失败: {e}")


async def _fetch_rates_uncached() -> RatesSnapshot:
    """实际网络拉取 + 兜底逻辑（不含缓存命中检查，不含单飞）

    被 fetch_rates 在缓存未命中时调用，多个并发请求通过单飞锁复用同一调用结果。
    """
    now = time.time()
    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
            resp = await client.get(_RATES_URL)
            data = resp.json()
        rates = data.get("datas")
        if not rates:
            raise ValueError("缺少 datas 字段")
        source_date = data.get("date")
        _cache["rates"] = rates
        _cache["fetched_at"] = now
        _cache["source_date"] = source_date
        _cache["is_stale"] = False  # 网络成功 → 新鲜
        _persist(rates, source_date)  # 落盘，作为重启后兜底
        logger.info(f"汇率已更新 ({source_date or '?'})")
        return RatesSnapshot(rates=rates, source_date=source_date, is_stale=False)
    except Exception as e:
        logger.error(f"获取汇率失败: {e}")
        # 兜底 1：内存旧值（哪怕已过期）
        if _cache["rates"]:
            logger.warning(f"使用内存过期汇率兜底（source_date={_cache['source_date']}）")
            return RatesSnapshot(
                rates=_cache["rates"], source_date=_cache["source_date"], is_stale=True
            )
        # 兜底 2：磁盘兜底（运行时缓存优先，其次种子文件）
        persisted = _load_persisted()
        if persisted:
            rates, source_date = persisted
            _cache["rates"] = rates  # 回填内存，避免反复读盘
            _cache["source_date"] = source_date
            _cache["is_stale"] = True
            return RatesSnapshot(rates=rates, source_date=source_date, is_stale=True)
        # 兜底 3：硬编码常量（种子文件也被删时的终极兜底，永不返回 None）
        logger.warning(f"磁盘兜底不可用，使用硬编码汇率 ({_HARDCODED_SOURCE_DATE})")
        _cache["rates"] = _HARDCODED_RATES
        _cache["source_date"] = _HARDCODED_SOURCE_DATE
        _cache["is_stale"] = True
        return RatesSnapshot(
            rates=_HARDCODED_RATES, source_date=_HARDCODED_SOURCE_DATE, is_stale=True
        )


async def fetch_rates(force_refresh: bool = False) -> RatesSnapshot:
    """获取实时汇率（USD 为基准），五级兜底 + 单飞

    兜底链：内存新鲜值（未过 TTL）→ 网络拉取 → 内存旧值（过期）→ 磁盘旧值
            （运行时缓存 + 种子文件）→ 硬编码常量

    单飞：N 个并发请求同时触发网络拉取时，只发 1 个请求，其余复用结果。

    Args:
        force_refresh: True 时跳过内存缓存，强制走网络（调度器定时刷新用）

    Returns:
        RatesSnapshot（rates 永不为空）；is_stale=True 表示走了兜底、汇率可能过时
    """
    now = time.time()
    # TTL 内缓存命中（force_refresh 跳过）
    if not force_refresh:
        if _cache["rates"] and (now - _cache["fetched_at"]) < _CACHE_TTL:
            return RatesSnapshot(
                rates=_cache["rates"],
                source_date=_cache["source_date"],
                is_stale=_cache.get("is_stale", False),
            )

    # 单飞：已有进行中的拉取任务则等它，否则自己发起
    global _inflight
    if _inflight is None or _inflight.done():
        _inflight = asyncio.create_task(_fetch_rates_uncached())
    return await _inflight


async def fetch_rates_snapshot() -> dict[str, float]:
    """快照场景：拿当前汇率快照（五级兜底永不返回空）

    Returns:
        完整 rates dict 拷贝，可冻结到快照里
    """
    snapshot = await fetch_rates()
    return dict(snapshot.rates)  # 拷贝一份避免外部改动影响缓存


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
    snapshot = await fetch_rates()
    return convert_with_rates(amount, from_ccy, to_ccy, snapshot.rates)


async def to_usd(amount: Decimal, from_currency: str) -> Decimal:
    """原币 → USD"""
    return await convert(amount, from_currency, "USD")


async def from_usd(amount: Decimal, to_currency: str) -> Decimal:
    """USD → 目标币种"""
    return await convert(amount, "USD", to_currency)


async def to_cny(amount: Decimal, from_currency: str) -> Decimal:
    """原币 → CNY（保留兼容旧调用）"""
    return await convert(amount, from_currency, "CNY")
