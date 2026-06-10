"""行情数据访问 — A股、美股、加密货币、基金"""

import abc

from sqlalchemy import select

from app.core.data_sources import (
    AkshareFundDataSource,
    CoinGlassDataSource,
    EastMoneyFundDataSource,
    SinaDataSource,
    TencentDataSource,
)
from app.core.database import async_session
from app.core.exceptions import BusinessError
from app.models.asset_quote import AssetQuote
from app.models.orm.asset_quote_orm import AssetQuoteRecord
from app.models.orm.asset_variety_orm import AssetVarietyRecord

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
    async def close(self):
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
                price=q.price,
                currency=q.currency,
                change_price=q.change_price if q.change_price is not None else None,
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
        raise BusinessError(40001, f"不支持的市场/数据源: market={market}, source={source}")

    async def close(self):
        """释放资源"""
        await self._sina.close()


class CryptoQuoteRepository(AssetQuoteRepository):
    """加密货币行情数据访问"""

    def __init__(self):
        self._source = CoinGlassDataSource()

    async def fetch_realtime_quote(
        self, codes: list[str], market: str = "CRYPTO", source: str = "coinglass"
    ) -> list[AssetQuote]:
        if source == "coinglass":
            return await self._source.fetch(codes, market="CRYPTO")
        raise BusinessError(40001, f"不支持的数据源: {source}")

    async def close(self):
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

        # CN 市场：区分 ETF（腾讯接口）和普通基金（天天基金）
        etf_set = await self._get_etf_tickers(codes)
        etf_codes = [c for c in codes if c in etf_set]
        fund_codes = [c for c in codes if c not in etf_set]

        results = []
        if etf_codes:
            results.extend(await self._tencent.fetch(etf_codes, market="CN"))
        if fund_codes:
            if source == "pingzhong":
                results.extend(await self._pingzhong.fetch(fund_codes, market="CN"))
            elif source == "akshare":
                results.extend(await self._akshare.fetch(fund_codes, market="CN"))
            else:
                raise BusinessError(40001, f"不支持的数据源: {source}")
        return results

    async def _get_etf_tickers(self, codes: list[str]) -> set[str]:
        """查询哪些代码属于 ETF（CN 市场）"""
        async with async_session() as session:
            rows = (await session.execute(
                select(AssetVarietyRecord.ticker).where(
                    AssetVarietyRecord.ticker.in_(codes),
                    AssetVarietyRecord.sub_category == "ETF",
                    AssetVarietyRecord.market == "CN",
                )
            )).all()
            return {row[0] for row in rows}

    async def close(self):
        pass


