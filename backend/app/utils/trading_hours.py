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
    """返回该市场行情缓存的 TTL（秒）— 兜底值

    缓存由后台定时任务（APScheduler）主动刷新，用户请求只读缓存。
    此 TTL 只是兜底——若调度器长期故障，超过 TTL 的旧缓存会被丢弃，
    降级到 DB 历史行情或 UNAVAILABLE。

    Args:
        market: "CN" / "US" / "CRYPTO" / "FUND"

    Returns:
        统一 5min（300s）。交易/非交易时段不再区分——调度器统一 30s 间隔保证新鲜度。
    """
    return 300  # 5min 兜底
