"""行情业务逻辑 — 统一处理 STOCK / CRYPTO / FUND 三种资产类别"""

from app.core.exceptions import BusinessError
from app.core.logger import logger
from app.models.asset_quote import AssetQuote
from app.repositories.asset_quote_repository import (
    CryptoQuoteRepository,
    FundQuoteRepository,
    StockQuoteRepository,
)


class AssetQuoteService:
    """行情业务逻辑"""

    _REPO_MAP = {
        "STOCK": StockQuoteRepository(),
        "CRYPTO": CryptoQuoteRepository(),
        "FUND": FundQuoteRepository(),
    }

    async def fetch_quotes(self, asset_class: str, market: str, codes: list[str]) -> list[AssetQuote]:
        """获取指定资产类别的实时行情

        Args:
            asset_class: "STOCK" / "CRYPTO" / "FUND"
            market: "CN" / "US" / "CRYPTO"
            codes: 标的代码列表
        """
        repo = self._REPO_MAP.get(asset_class)
        if not repo:
            raise BusinessError(400, f"不支持的资产类别: {asset_class}")

        quotes = await repo.fetch_realtime_quote(codes, market=market)
        if quotes:
            saved = await repo.save_asset_quotes(quotes)
            logger.info(f"已保存 {saved} 条 {asset_class}({market}) 行情")
        return quotes
