"""交易时段判定 — 各市场是否在交易时段，用于行情缓存 TTL

项目用本地时间（部署环境为北京时间），不引入时区库。
美股交易时段按北京时间 21:30-04:00 写死，夏令时差1小时未处理（看板场景可接受）。
节假日不处理 — 节假日走非交易长缓存，价格本就不动，影响可忽略。
"""

from datetime import datetime


def is_trading_hours(market: str, now: datetime | None = None) -> bool:
    """判断指定市场当前是否在交易时段（北京时间，本地时间）

    Args:
        market: "CN" / "US" / "CRYPTO"
        now: 当前时间，默认 datetime.now()

    Returns:
        是否在交易时段。CRYPTO 恒为 True（7×24）；CN/US 按工作日时段判定。
    """
    now = now or datetime.now()
    if market == "CRYPTO":
        return True  # 7×24 全天候
    if now.weekday() >= 5:
        return False  # 周六日休市
    hm = now.hour * 60 + now.minute  # 当天分钟数
    if market == "CN":
        # A股：上午 9:30-11:30 / 下午 13:00-15:00
        return (570 <= hm < 690) or (780 <= hm < 900)
    if market == "US":
        # 美股：北京时间 21:30-次日 04:00（跨日，夏令时差1小时未处理）
        return hm >= 1290 or hm < 240
    return False


def quote_cache_ttl(market: str) -> int:
    """返回该市场行情缓存的 TTL（秒）

    Args:
        market: "CN" / "US" / "CRYPTO" / "FUND"

    Returns:
        交易时段 30s（看板场景足够新鲜），非交易时段 30min（价格不动）；
        基金固定 15min（净值日更，无交易时段概念）。
    """
    if market == "FUND":
        return 900  # 15min
    return 30 if is_trading_hours(market) else 1800
