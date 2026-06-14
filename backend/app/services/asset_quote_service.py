"""行情业务逻辑 — STOCK / CRYPTO / FUND 三类行情"""

from app.core.logger import logger
from app.models.asset_quote import AssetQuote
from app.repositories.asset_quote_repository import (
    CryptoQuoteRepository,
    FundQuoteRepository,
    StockQuoteRepository,
)
from app.repositories.asset_variety_repository import AssetVarietyRepository

# 基金净值数据按天更新（晚上才出当日净值），15 分钟内反复拉同一只基金没意义
FUND_CACHE_MAX_AGE_MINUTES = 15


class AssetQuoteService:
    """行情业务逻辑"""

    def __init__(self):
        self._stock_repo = StockQuoteRepository()
        self._crypto_repo = CryptoQuoteRepository()
        self._fund_repo = FundQuoteRepository()

    async def fetch_stock_quotes(self, market: str, codes: list[str]) -> list[AssetQuote]:
        """获取股票行情（A股/美股）

        Args:
            market: "CN" / "US"
            codes: 标的代码列表
        """
        quotes = await self._stock_repo.fetch_realtime_quote(codes, market=market)
        if market == "US" and quotes:
            await self._enrich_names(quotes)
        # 统一补 asset_class（DataSource 不感知品种类别，由调用方语义决定）
        for q in quotes:
            q.asset_class = "STOCK"
        if quotes:
            saved = await self._stock_repo.save_asset_quotes(quotes)
            logger.info(f"已保存 {saved} 条 STOCK({market}) 行情")
        return quotes

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

    async def fetch_crypto_quotes(self, codes: list[str]) -> list[AssetQuote]:
        """获取加密货币行情"""
        quotes = await self._crypto_repo.fetch_realtime_quote(codes, market="CRYPTO")
        for q in quotes:
            q.asset_class = "CRYPTO"
        if quotes:
            saved = await self._crypto_repo.save_asset_quotes(quotes)
            logger.info(f"已保存 {saved} 条 CRYPTO 行情")
        return quotes

    async def fetch_fund_quotes(self, market: str, codes: list[str]) -> list[AssetQuote]:
        """获取基金净值（CN 走天天基金，US 走腾讯）

        缓存策略：基金净值按天更新（且常常晚上才出当日净值），高频轮询无意义。
        先查 asset_quote 表里近 15 分钟内入库的快照；命中的直接复用，未命中
        的 ticker 才走网络，最后合并返回。

        Args:
            market: "CN" / "US"
            codes: 基金代码列表
        """
        # 1) 命中缓存
        cached = await self._fund_repo.get_recent_quotes(
            "FUND", market, codes, max_age_minutes=FUND_CACHE_MAX_AGE_MINUTES,
        )
        missing = [c for c in codes if c not in cached]

        if not missing:
            logger.info(f"FUND({market}) 全部 {len(codes)} 只命中缓存，跳过网络请求")
            return list(cached.values())

        if cached:
            logger.info(
                f"FUND({market}) 命中缓存 {len(cached)} 只，未命中 {len(missing)} 只走网络"
            )

        # 2) 未命中部分走网络
        fresh = await self._fund_repo.fetch_realtime_quote(missing, market=market)
        for q in fresh:
            q.asset_class = "FUND"
        if fresh:
            saved = await self._fund_repo.save_asset_quotes(fresh)
            logger.info(f"已保存 {saved} 条 FUND({market}) 行情")

        # 3) 合并：缓存 + 新拉
        return list(cached.values()) + fresh

    async def fetch_quotes_by_asset_class(
        self, asset_class: str, market: str, tickers: list[str]
    ) -> list[AssetQuote]:
        """按资产类别批量获取行情（统一路由入口）

        Args:
            asset_class: "STOCK" / "FUND" / "CRYPTO"
            market: "CN" / "US" / "CRYPTO"
            tickers: 标的代码列表
        """
        if asset_class == "STOCK":
            return await self.fetch_stock_quotes(market, tickers)
        if asset_class == "FUND":
            return await self.fetch_fund_quotes(market, tickers)
        if asset_class == "CRYPTO":
            return await self.fetch_crypto_quotes(tickers)
        logger.warning(f"不支持的资产类别: {asset_class}")
        return []
