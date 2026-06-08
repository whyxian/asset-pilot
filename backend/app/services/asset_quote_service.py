"""股票行情业务逻辑 — 统一处理 A股 / 美股 / 基金"""

import asyncio

from app.core.exceptions import BusinessError
from app.core.logger import logger
from app.models.asset_quote import AssetQuote
from app.repositories.asset_quote_repository import (
    CryptoQuoteRepository,
    FundQuoteRepository,
    StockQuoteRepository,
)


class AssetQuoteService:
    """股票行情业务逻辑"""

    _MARKET_CONFIG = {
        "CN": ("A", None),
        "US": ("US", None),
        "CRYPTO": (None, "coinglass"),
        "FUND": (None, "pingzhong"),
    }

    def __init__(self):
        self._stock_repo = StockQuoteRepository()
        self._crypto_repo = CryptoQuoteRepository()
        self._fund_repo = FundQuoteRepository()

    async def fetch_market_quotes(self, market: str, codes: list[str]) -> list[AssetQuote]:
        """获取指定市场的实时行情

        Args:
            market: "CN" / "US" / "CRYPTO" / "FUND"
            codes: 标的代码列表
        """
        if market in ("CN", "US"):
            mk, _ = self._MARKET_CONFIG[market]
            repo = self._stock_repo
            quotes = await repo.fetch_realtime_quote(codes, market=mk)
        elif market == "CRYPTO":
            repo = self._crypto_repo
            quotes = await repo.fetch_realtime_quote(codes)
        elif market == "FUND":
            repo = self._fund_repo
            quotes = await repo.fetch_realtime_quote(codes)
        else:
            raise BusinessError(400, f"不支持的市场类型: {market}")
        if quotes:
            saved = await repo.save_asset_quotes(quotes)
            logger.info(f"已保存 {saved} 条 {market} 行情")
        return quotes

    async def fetch_all_quotes(
        self,
        cn: list[str] | None = None,
        us: list[str] | None = None,
        crypto: list[str] | None = None,
        fund: list[str] | None = None,
    ) -> dict[str, list[AssetQuote]]:
        """同时获取多市场行情

        Args:
            cn: A 股代码列表
            us: 美股代码列表
            crypto: 加密货币 ID 列表
            fund: 基金代码列表

        Returns:
            {"CN": [...], "US": [...], "CRYPTO": [...], "FUND": [...]}
        """
        tasks = []
        markets = []

        if cn:
            tasks.append(self._stock_repo.fetch_realtime_quote(cn, market="A"))
            markets.append("CN")
        if us:
            tasks.append(self._stock_repo.fetch_realtime_quote(us, market="US"))
            markets.append("US")
        if crypto:
            tasks.append(self._crypto_repo.fetch_realtime_quote(crypto))
            markets.append("CRYPTO")
        if fund:
            tasks.append(self._fund_repo.fetch_realtime_quote(fund))
            markets.append("FUND")

        if not tasks:
            return {}

        results = await asyncio.gather(*tasks)
        market_quotes = dict(zip(markets, results))

        # 保存到数据库
        repo_map = {
            "CN": self._stock_repo,
            "US": self._stock_repo,
            "CRYPTO": self._crypto_repo,
            "FUND": self._fund_repo,
        }
        for market, quotes in market_quotes.items():
            if quotes:
                saved = await repo_map[market].save_asset_quotes(quotes)
                logger.info(f"已保存 {saved} 条 {market} 行情")

        return market_quotes