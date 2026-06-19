"""行情与汇率后台定时预热 — APScheduler 定时拉数据 + 写缓存

设计：用户请求永远只读缓存，后台任务持续刷新。完全解耦用户请求和数据源调用。
刷新频率按市场+交易时段区分：交易时段必刷，非交易跳过，基金 15min 一次。
建仓是唯一的用户行为→数据源场景（低频，create_holding 自行拉行情 + 写缓存）。
配置统一在 SchedulerConfig（app/core/scheduler_config.py）。
"""

import time

from app.core.logger import logger
from app.core.scheduler_config import SchedulerConfig
from app.repositories.asset_holding_repository import AssetHoldingRepository
from app.services.asset_quote_service import AssetQuoteService
from app.utils.exchange_rate import fetch_rates
from app.utils.quote_cache import quote_cache
from app.utils.trading_hours import is_trading_hours


class QuoteScheduler:
    """行情与汇率定时刷新器 — 在 FastAPI lifespan 中启动/关闭"""

    def __init__(self):
        self._holding_repo = AssetHoldingRepository()
        self._quote_svc = AssetQuoteService()
        self._last_refresh: dict[str, float] = {}  # {market: last_refresh_timestamp}

    def _needs_refresh(self, market: str) -> bool:
        """判断该市场现在是否需要刷新

        交易时段（含加密 7×24）→ 必刷新；基金 → 超 15min 才刷；非交易 → 超 30min 才刷。
        """
        now = time.time()
        last = self._last_refresh.get(market, 0)
        if is_trading_hours(market):
            return True  # 交易时段按调度器频率（30s）必刷
        if market == "FUND":
            return (now - last) >= SchedulerConfig.FUND_REFRESH_INTERVAL
        return (now - last) >= SchedulerConfig.NON_TRADING_REFRESH_INTERVAL

    async def refresh_quotes(self) -> None:
        """拉所有活跃持仓的实时行情，按市场+交易时段决定是否刷新"""
        groups = await self._holding_repo.list_all_tickers()
        if not groups:
            return

        now = time.time()
        for (ac, market), tickers in groups.items():
            if not self._needs_refresh(market):
                continue

            self._last_refresh[market] = now
            try:
                quotes = await self._quote_svc.fetch_quotes_by_asset_class(
                    ac, market, tickers, force_refresh=True,
                )
                if quotes:
                    quote_cache.set(market, quotes)
                    logger.info(f"[QuoteScheduler] {ac}/{market} 刷新 {len(quotes)} 只行情")
            except Exception as e:
                logger.error(f"[QuoteScheduler] {ac}/{market} 网络失败: {e}，查 DB 历史兜底")
                try:
                    repo = self._quote_svc._get_repo(ac)
                    historical = await repo.get_latest_quotes(ac, market, tickers)
                    if historical:
                        quote_cache.set(market, list(historical.values()))
                        logger.info(f"[QuoteScheduler] {ac}/{market} 用 DB 历史兜底 {len(historical)} 只")
                    else:
                        logger.warning(f"[QuoteScheduler] {ac}/{market} 网络+DB 均无数据")
                except Exception as e2:
                    logger.error(f"[QuoteScheduler] {ac}/{market} DB 兜底也失败: {e2}")

    async def refresh_rates(self) -> None:
        """force_refresh 绕过 1h 缓存，强制走网络拉最新汇率写入缓存"""
        try:
            snapshot = await fetch_rates(force_refresh=True)
            logger.info(f"[QuoteScheduler] 汇率已刷新 (source_date={snapshot.source_date}, stale={snapshot.is_stale})")
        except Exception as e:
            logger.error(f"[QuoteScheduler] 汇率刷新失败: {e}")
