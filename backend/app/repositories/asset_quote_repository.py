"""行情数据访问 — A股、美股、加密货币、基金"""

import abc
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.core.data_sources import (
    AkshareFundDataSource,
    CoinGlassDataSource,
    EastMoneyFundDataSource,
    SinaDataSource,
    TencentDataSource,
)
from app.core.database import async_session
from app.core.exceptions import BusinessError
from app.core.error_codes import CODE_VALIDATION, CODE_NOT_FOUND
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

        使用 INSERT OR IGNORE — 撞 UNIQUE(asset_class, market, ticker, timestamp)
        静默跳过（同一天/同一时刻反复拉行情是常态，不应报错）。

        Args:
            quotes: 行情数据列表

        Returns:
            实际新增的条数（重复跳过的不计）
        """
        if not quotes:
            return 0
        rows = [
            {
                "ticker": q.ticker,
                "asset_class": q.asset_class,
                "market": q.market,
                "name": q.name,
                "price": q.price,
                "currency": q.currency,
                "change_price": q.change_price,
                "change_ratio": q.change_ratio,
                "timestamp": q.updated_at,
                "source": q.source,
            }
            for q in quotes
        ]
        async with async_session() as session:
            stmt = sqlite_insert(AssetQuoteRecord).values(rows)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["asset_class", "market", "ticker", "timestamp"],
            )
            result = await session.execute(stmt)
            await session.commit()
            # rowcount 反映实际插入条数（SQLite ON CONFLICT DO NOTHING 会返回 0 那部分）
            return result.rowcount or 0

    async def get_recent_quotes(
        self,
        asset_class: str,
        market: str,
        tickers: list[str],
        max_age_minutes: int = 15,
    ) -> dict[str, AssetQuote]:
        """查询近期行情缓存 — 用于避免短时间内反复拉网络。

        在 asset_quote 表中找 created_at 落在 [now - max_age_minutes, now] 内
        的最新一条记录，按 ticker 返回。**用 created_at（入库时间）而非 timestamp**，
        因为基金的 timestamp 是净值日期（00:00:00），用它判断"近 15 分钟"无意义。

        Args:
            asset_class: 资产类别
            market: 市场
            tickers: 代码列表
            max_age_minutes: 缓存有效期（分钟）

        Returns:
            {ticker: AssetQuote}，未命中的 ticker 不在 dict 中
        """
        if not tickers:
            return {}
        cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
        async with async_session() as session:
            # 取该批 ticker 在 cutoff 之后入库的最新一条；按 created_at 倒序拿第一条
            records = (await session.execute(
                select(AssetQuoteRecord)
                .where(
                    AssetQuoteRecord.asset_class == asset_class,
                    AssetQuoteRecord.market == market,
                    AssetQuoteRecord.ticker.in_(tickers),
                    AssetQuoteRecord.created_at >= cutoff,
                )
                .order_by(AssetQuoteRecord.ticker, desc(AssetQuoteRecord.created_at))
            )).scalars().all()
        # 同一 ticker 可能有多条；按 created_at desc 排序，第一次见到就是最新
        result: dict[str, AssetQuote] = {}
        for r in records:
            if r.ticker in result:
                continue
            result[r.ticker] = AssetQuote(
                ticker=r.ticker,
                asset_class=r.asset_class,
                market=r.market,
                name=r.name,
                price=Decimal(str(r.price)),
                currency=r.currency,
                change_price=Decimal(str(r.change_price)) if r.change_price is not None else None,
                change_ratio=r.change_ratio,
                updated_at=r.timestamp,
                source=r.source,
            )
        return result

    async def get_latest_quotes(
        self,
        asset_class: str,
        market: str,
        tickers: list[str],
    ) -> dict[str, AssetQuote]:
        """查询每个 ticker 的最新一条历史行情（不限时间，用于实时失败时兜底）

        与 get_recent_quotes 的区别：不限 created_at 窗口，取每个 ticker 入库最新的一条。
        建仓时强制落库保证 DB 有该 ticker 的历史行情，实时拉取失败时回查此处兜底。

        Args:
            asset_class: 资产类别
            market: 市场
            tickers: 代码列表

        Returns:
            {ticker: AssetQuote}，DB 里没有的 ticker 不在 dict 中
        """
        if not tickers:
            return {}
        async with async_session() as session:
            records = (await session.execute(
                select(AssetQuoteRecord)
                .where(
                    AssetQuoteRecord.asset_class == asset_class,
                    AssetQuoteRecord.market == market,
                    AssetQuoteRecord.ticker.in_(tickers),
                )
                .order_by(AssetQuoteRecord.ticker, desc(AssetQuoteRecord.created_at))
            )).scalars().all()
        # 同一 ticker 可能有多条；按 created_at desc，第一次见到就是最新
        result: dict[str, AssetQuote] = {}
        for r in records:
            if r.ticker in result:
                continue
            result[r.ticker] = AssetQuote(
                ticker=r.ticker,
                asset_class=r.asset_class,
                market=r.market,
                name=r.name,
                price=Decimal(str(r.price)),
                currency=r.currency,
                change_price=Decimal(str(r.change_price)) if r.change_price is not None else None,
                change_ratio=r.change_ratio,
                updated_at=r.timestamp,
                source=r.source,
            )
        return result


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
        raise BusinessError(CODE_VALIDATION, f"不支持的市场/数据源: market={market}, source={source}")

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
        raise BusinessError(CODE_VALIDATION, f"不支持的数据源: {source}")

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
                raise BusinessError(CODE_VALIDATION, f"不支持的数据源: {source}")
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


