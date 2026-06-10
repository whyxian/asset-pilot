"""行情数据访问 — A股、美股、加密货币、基金"""

import abc
import asyncio

from app.core.data_sources import (
    AkshareFundDataSource,
    CoinGlassDataSource,
    EastMoneyFundDataSource,
    QuoteDataSource,
    SinaDataSource,
    TencentDataSource,
)
from app.core.database import async_session
from app.core.exceptions import BusinessError
from app.models.asset_quote import AssetQuote
from app.models.orm.asset_quote_orm import AssetQuoteRecord

class AssetQuoteRepository(abc.ABC):
    """行情数据访问抽象基类"""

    @abc.abstractmethod
    async def fetch_realtime_quote(self, codes: list[str], market: str) -> list[AssetQuote]:
        """批量获取实时行情

        Args:
            codes: 标的代码列表
            market: "CN" / "US" / "CRYPTO"
        """

    @abc.abstractmethod
    def close(self):
        """释放资源"""
        ...

    async def save_asset_quotes(self, quotes: list[AssetQuote]) -> int:
        """保存行情数据到 asset_quote 表

        Args:
            quotes: 行情数据列表

        Returns:
            写入条数
        """
        records = [
            AssetQuoteRecord(
                ticker=q.ticker,
                market=q.market,
                name=q.name,
                price=float(q.price),
                currency=q.currency,
                change_price=float(q.change_price) if q.change_price else None,
                change_ratio=q.change_ratio,
                timestamp=q.updated_at,
                source=q.source,
            )
            for q in quotes
        ]
        async with async_session() as session:
            session.add_all(records)
            await session.commit()
        return len(records)


class StockQuoteRepository(AssetQuoteRepository):
    """股票行情数据访问 — A 股 + 美股"""

    def __init__(self):
        self._tencent = TencentDataSource()
        self._sina = SinaDataSource()

    async def fetch_realtime_quote(
        self, codes: list[str], market: str = "CN", source: str = "tencent"
    ) -> list[AssetQuote]:
        """批量获取股票行情

        Args:
            codes: 代码列表
            market: "CN" / "US"
            source: "tencent"（默认） / "sina"（仅美股备选）
        """
        if market == "CN":
            return await self._tencent.fetch(codes, market="CN")
        if market == "US":
            if source == "tencent":
                return await self._tencent.fetch(codes, market="US")
            if source == "sina":
                return await self._sina.fetch(codes, market="US")
        raise BusinessError(400, f"不支持的市场/数据源: market={market}, source={source}")

    def close(self):
        """释放资源"""
        self._sina.close()


class CryptoQuoteRepository(AssetQuoteRepository):
    """加密货币行情数据访问"""

    def __init__(self):
        self._source = CoinGlassDataSource()

    async def fetch_realtime_quote(
        self, codes: list[str], market: str = "CRYPTO", source: str = "coinglass"
    ) -> list[AssetQuote]:
        if source == "coinglass":
            return await self._source.fetch(codes, market="CRYPTO")
        raise BusinessError(400, f"不支持的数据源: {source}")

    def close(self):
        pass


class FundQuoteRepository(AssetQuoteRepository):
    """基金行情数据访问"""

    def __init__(self):
        self._pingzhong = EastMoneyFundDataSource()
        self._akshare = AkshareFundDataSource()
        self._tencent = TencentDataSource()

    async def fetch_realtime_quote(
        self, codes: list[str], market: str = "CN", source: str = "pingzhong"
    ) -> list[AssetQuote]:
        if market == "US":
            return await self._tencent.fetch(codes, market="US")
        if source == "pingzhong":
            return await self._pingzhong.fetch(codes, market="CN")
        if source == "akshare":
            return await self._akshare.fetch(codes, market="CN")
        raise BusinessError(400, f"不支持的数据源: {source}")

    def close(self):
        pass


