"""行情与汇率后台定时预热 — APScheduler 定时拉数据 + 写缓存

设计：用户请求永远只读缓存，后台任务持续刷新。完全解耦用户请求和数据源调用。
建仓是唯一的用户行为→数据源场景（低频，create_holding 自行拉行情 + 写缓存）。
"""

from app.core.logger import logger
from app.repositories.asset_holding_repository import AssetHoldingRepository
from app.services.asset_quote_service import AssetQuoteService
from app.utils.exchange_rate import fetch_rates
from app.utils.quote_cache import quote_cache


class QuoteScheduler:
    """行情与汇率定时刷新器 — 在 FastAPI lifespan 中启动/关闭"""

    def __init__(self):
        self._holding_repo = AssetHoldingRepository()
        self._quote_svc = AssetQuoteService()

    async def refresh_quotes(self) -> None:
        """拉所有活跃持仓的实时行情，失败时回退 DB 历史——保证缓存永不过期，用户请求永不触网"""
        groups = await self._holding_repo.list_all_tickers()
        if not groups:
            return  # 无持仓，不浪费网络请求

        total_tickers = sum(len(tks) for tks in groups.values())
        logger.info(f"[QuoteScheduler] 开始定时刷新 {total_tickers} 个品种行情...")

        for (ac, market), tickers in groups.items():
            try:
                quotes = await self._quote_svc.fetch_quotes_by_asset_class(
                    ac, market, tickers, force_refresh=True,
                )
                if quotes:
                    quote_cache.set(market, quotes)
                    logger.info(f"[QuoteScheduler] {ac}/{market} 刷新 {len(quotes)} 只行情")
            except Exception as e:
                # 网络失败 → 查 DB 历史，保证缓存不空、用户请求永不打网络
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
