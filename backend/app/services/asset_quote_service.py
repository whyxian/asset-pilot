"""行情业务逻辑 — STOCK / CRYPTO / FUND 三类行情"""

import asyncio

from app.core.logger import logger
from app.core.scheduler_config import SchedulerConfig
from app.models.asset_quote import AssetQuote, QuoteStatus
from app.repositories.asset_quote_repository import (
    CryptoQuoteRepository,
    FundQuoteRepository,
    StockQuoteRepository,
)
from app.repositories.asset_variety_repository import AssetVarietyRepository
from app.utils.quote_cache import quote_cache

# 行情并发拉取整体熔断阈值（统一在 SchedulerConfig.QUOTE_FETCH_TIMEOUT）
QUOTE_FETCH_TIMEOUT = SchedulerConfig.QUOTE_FETCH_TIMEOUT


class AssetQuoteService:
    """行情业务逻辑"""

    def __init__(self):
        self._stock_repo = StockQuoteRepository()
        self._crypto_repo = CryptoQuoteRepository()
        self._fund_repo = FundQuoteRepository()
        # 行情内存缓存（进程级单例，定时任务和请求处理共享）
        self._cache = quote_cache

    async def fetch_quote_map_concurrent(
        self,
        groups: dict[tuple[str, str], list[str]],
        force_refresh: bool = False,
        timeout: float = QUOTE_FETCH_TIMEOUT,
    ) -> dict[tuple[str, str, str], tuple[AssetQuote, QuoteStatus]]:
        """各资产组并发拉取行情，整体超时熔断 + 单组异常容错 + 失败降级 DB 历史

        供 overview / holdings / snapshot 等多组行情场景共用。实时拉取失败的 ticker
        反推后回查 DB 历史行情兜底（建仓强制落库保证有历史），最差也有历史数据，
        不再兜底 0 误导。三元组 key 避免不同品种 ticker 冲突。

        Args:
            groups: {(asset_class, market): [tickers]}
            force_refresh: 是否强制刷新绕过基金 15 分钟缓存
            timeout: 整体超时秒数，None 表示不超时

        Returns:
            {(asset_class, market, ticker): (AssetQuote, QuoteStatus)}；
            REALTIME=实时，HISTORICAL=DB 历史兜底；连历史都没有的 ticker 不在 map
            （调用方视为 UNAVAILABLE）。
        """
        tasks = {
            asyncio.create_task(
                self.fetch_quotes_by_asset_class(ac, market, tickers, force_refresh=force_refresh)
            ): (ac, market, tickers)
            for (ac, market), tickers in groups.items()
        }
        try:
            done, pending = await asyncio.wait(
                tasks, timeout=timeout, return_when=asyncio.ALL_COMPLETED
            )
        except Exception as e:
            logger.error(f"行情拉取异常: {e}")
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            # 全部失败 → 所有 ticker 走 DB 历史降级
            return await self._fallback_all_to_history(groups)

        # 取消超时未完成的组，并 await 收尾以消费 CancelledError、清理协程内连接
        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
            logger.warning(
                f"行情拉取超时({timeout}s)，丢弃组: "
                f"{[tasks[t][:2] for t in pending]}，已获取 {len(done)} 组"
            )

        quote_map: dict[tuple[str, str, str], tuple[AssetQuote, QuoteStatus]] = {}
        for t in done:
            ac, market, tickers = tasks[t]
            realtime_quotes: list[AssetQuote] = []
            if not t.exception():
                realtime_quotes = t.result()
            else:
                logger.error(f"行情组 {ac}/{market} 拉取失败: {t.exception()}")

            # 实时成功的标记 REALTIME
            got_tickers: set[str] = set()
            for q in realtime_quotes:
                quote_map[(ac, market, q.ticker)] = (q, QuoteStatus.REALTIME)
                got_tickers.add(q.ticker)

            # 反推失败 ticker（请求 - 实时拿到的），查 DB 历史降级
            missing = [tk for tk in tickers if tk not in got_tickers]
            if missing:
                historical = await self._get_repo(ac).get_latest_quotes(ac, market, missing)
                for tk, q in historical.items():
                    quote_map[(ac, market, tk)] = (q, QuoteStatus.HISTORICAL)
                    logger.info(f"{ac}/{market}/{tk} 实时失败，使用 DB 历史行情兜底")
                # 连历史都没有的 ticker 不进 map（调用方视为 UNAVAILABLE）
        return quote_map

    def _get_repo(self, asset_class: str):
        """按资产类别取对应 repo（用于降级查 DB 历史）"""
        if asset_class == "STOCK":
            return self._stock_repo
        if asset_class == "FUND":
            return self._fund_repo
        return self._crypto_repo

    async def _fallback_all_to_history(
        self, groups: dict[tuple[str, str], list[str]]
    ) -> dict[tuple[str, str, str], tuple[AssetQuote, QuoteStatus]]:
        """全部组失败时，所有 ticker 走 DB 历史降级"""
        quote_map: dict[tuple[str, str, str], tuple[AssetQuote, QuoteStatus]] = {}
        for (ac, market), tickers in groups.items():
            if not tickers:
                continue
            historical = await self._get_repo(ac).get_latest_quotes(ac, market, tickers)
            for tk, q in historical.items():
                quote_map[(ac, market, tk)] = (q, QuoteStatus.HISTORICAL)
                logger.info(f"{ac}/{market}/{tk} 实时失败，使用 DB 历史行情兜底")
        return quote_map

    async def fetch_stock_quotes(
        self, market: str, codes: list[str], force_refresh: bool = False
    ) -> list[AssetQuote]:
        """获取股票行情（A股/美股）

        缓存策略：内存缓存按 (market, ticker) 单条存，TTL 按交易时段（交易 30s /
        非交易 30min）。部分命中，只拉缺失的 ticker。force_refresh 跳过缓存。

        Args:
            market: "CN" / "US"
            codes: 标的代码列表
            force_refresh: True 时跳过缓存，强制全部走网络拉最新行情        """
        # 1) 部分命中缓存（force_refresh 时全部视为缺失；过期数据照常返回不触网）
        hit, missing, _stale = ({}, codes, set()) if force_refresh else self._cache.get(market, codes)
        if not missing:
            logger.info(f"STOCK({market}) 全部 {len(hit)} 只命中缓存，跳过网络")
            return list(hit.values())

        # 2) 未命中部分走网络（仅从未缓存过的 ticker，调度器正常时走不到）
        fresh = await self._stock_repo.fetch_realtime_quote(missing, market=market)
        if market == "US" and fresh:
            await self._enrich_names(fresh)
        # 统一补 asset_class（DataSource 不感知品种类别，由调用方语义决定）
        for q in fresh:
            q.asset_class = "STOCK"
        if fresh:
            saved = await self._stock_repo.save_asset_quotes(fresh)
            logger.info(f"已保存 {saved} 条 STOCK({market}) 行情")
            self._cache.set(market, fresh)  # force_refresh 也写缓存

        if hit:
            logger.info(f"STOCK({market}) 命中缓存 {len(hit)} 只，未命中 {len(missing)} 只走网络")
        return list(hit.values()) + fresh

    async def _enrich_names(self, quotes: list[AssetQuote]):
        """用 DB 中的英文名称替换腾讯 API 返回的中文名称

        Args:
            quotes: 行情列表（会原地修改 name 字段）
        """
        tickers = [q.ticker for q in quotes]
        name_map = await AssetVarietyRepository().get_name_map(tickers)
        for q in quotes:
            if q.ticker in name_map:
                q.name = name_map[q.ticker]

    async def fetch_crypto_quotes(
        self, codes: list[str], force_refresh: bool = False
    ) -> list[AssetQuote]:
        """获取加密货币行情

        缓存策略：内存缓存按 (CRYPTO, ticker) 单条存，TTL 30s（7×24 交易）。
        部分命中，只拉缺失的 ticker。force_refresh 跳过缓存。

        Args:
            codes: 标的代码列表
            force_refresh: True 时跳过缓存，强制全部走网络        """
        hit, missing, _stale = ({}, codes, set()) if force_refresh else self._cache.get("CRYPTO", codes)
        if not missing:
            logger.info(f"CRYPTO 全部 {len(hit)} 只命中缓存，跳过网络")
            return list(hit.values())

        fresh = await self._crypto_repo.fetch_realtime_quote(missing, market="CRYPTO")
        for q in fresh:
            q.asset_class = "CRYPTO"
        if fresh:
            saved = await self._crypto_repo.save_asset_quotes(fresh)
            logger.info(f"已保存 {saved} 条 CRYPTO 行情")
            self._cache.set("CRYPTO", fresh)  # force_refresh 也写缓存

        if hit:
            logger.info(f"CRYPTO 命中缓存 {len(hit)} 只，未命中 {len(missing)} 只走网络")
        return list(hit.values()) + fresh

    async def fetch_fund_quotes(
        self, market: str, codes: list[str], force_refresh: bool = False
    ) -> list[AssetQuote]:
        """获取基金净值（CN 走天天基金，US 走腾讯）

        缓存策略：基金净值按天更新（且常常晚上才出当日净值），高频轮询无意义。
        内存缓存按 (FUND, ticker) 单条存，TTL 15min。部分命中，只拉缺失的 ticker。
        force_refresh 跳过缓存。save_asset_quotes 仍写 DB 作历史快照。

        Args:
            market: "CN" / "US"
            codes: 基金代码列表
            force_refresh: True 时跳过 15 分钟缓存，强制全部走网络拉最新净值        """
        # 1) 部分命中内存缓存（force_refresh 时全部视为缺失）
        hit, missing, _stale = ({}, codes, set()) if force_refresh else self._cache.get("FUND", codes)
        if not missing:
            logger.info(f"FUND({market}) 全部 {len(hit)} 只命中缓存，跳过网络请求")
            return list(hit.values())

        # 2) 未命中部分走网络
        fresh = await self._fund_repo.fetch_realtime_quote(missing, market=market)
        for q in fresh:
            q.asset_class = "FUND"
        if fresh:
            saved = await self._fund_repo.save_asset_quotes(fresh)
            logger.info(f"已保存 {saved} 条 FUND({market}) 行情")
            self._cache.set("FUND", fresh)  # force_refresh 也写缓存

        if hit:
            logger.info(f"FUND({market}) 命中缓存 {len(hit)} 只，未命中 {len(missing)} 只走网络")
        return list(hit.values()) + fresh

    async def fetch_quotes_by_asset_class(
        self, asset_class: str, market: str, tickers: list[str], force_refresh: bool = False
    ) -> list[AssetQuote]:
        """按资产类别批量获取行情（统一路由入口）

        Args:
            asset_class: "STOCK" / "FUND" / "CRYPTO"
            market: "CN" / "US" / "CRYPTO"
            tickers: 标的代码列表
            force_refresh: True 时绕过基金 15 分钟缓存强制走网络（股票/加密货币本就无缓存）
        """
        if asset_class == "STOCK":
            return await self.fetch_stock_quotes(market, tickers, force_refresh=force_refresh)
        if asset_class == "FUND":
            return await self.fetch_fund_quotes(market, tickers, force_refresh=force_refresh)
        if asset_class == "CRYPTO":
            return await self.fetch_crypto_quotes(tickers, force_refresh=force_refresh)
        logger.warning(f"不支持的资产类别: {asset_class}")
        return []
