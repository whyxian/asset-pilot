"""自选股业务逻辑

收藏时若品种不存在，同一事务内自动注册到 asset_varieties（建仓/搜索可用）；
with-quotes 复用 fetch_quote_map_concurrent 三态链路（QuoteCache → DB 历史 → UNAVAILABLE）。
"""

from app.core.logger import logger
from app.models.asset_quote import QuoteStatus
from app.models.asset_variety import AssetVarietyCreate
from app.models.asset_watchlist import WatchlistCreate, WatchlistItem, WatchlistWithQuote
from app.repositories.asset_variety_repository import AssetVarietyRepository
from app.repositories.watchlist_repository import WatchlistRepository
from app.services.asset_quote_service import AssetQuoteService


class WatchlistService:
    """自选股业务逻辑"""

    def __init__(self):
        self._repo = WatchlistRepository()
        self._variety_repo = AssetVarietyRepository()
        self._quote_svc = AssetQuoteService()

    async def list_watchlist(self) -> list[WatchlistItem]:
        """自选列表（收藏时间倒序）"""
        return await self._repo.list_watchlist()

    async def create_watchlist(self, data: WatchlistCreate) -> WatchlistItem:
        """收藏 — 幂等；品种不存在时自动注册；分类按市场规则对齐

        市场规则（2026-08-10 用户确认）：
        - US / CRYPTO：ticker 不重复 → 按 ticker 查品种并**对齐其分类**
          （SPY 以 STOCK 查询、库里是 FUND → 收藏记录用 FUND，不注册新分类）
        - CN：FUND/STOCK/ETF 可能重复（000001）→ 按三元组精确匹配，查询分类为准
        """
        # 1. 按市场规则解析品种：CN 三元组 / US·CRYPTO ticker 级
        if data.market == "CN":
            variety = await self._variety_repo.get_variety(data.ticker, data.asset_class, data.market)
        else:
            variety = await self._variety_repo.get_variety(data.ticker)

        # 2. 确定最终三元组 + 名称：US/CRYPTO 且库里已有 → 对齐库里分类
        if variety is not None:
            asset_class = variety.asset_class
            market = variety.market
            name = variety.name or data.name
            if data.market != "CN" and (asset_class != data.asset_class or market != data.market):
                logger.info(
                    f"收藏 {data.ticker} 对齐品种分类 {data.asset_class}/{data.market} → {asset_class}/{market}"
                )
        else:
            asset_class = data.asset_class
            market = data.market
            name = data.name
            # 3. 品种不存在 → 自动注册（复用品种创建逻辑；CN 注册查询三元组，US/CRYPTO 注册查询分类）
            try:
                await self._variety_repo.create_variety(AssetVarietyCreate(
                    ticker=data.ticker,
                    name=data.name or data.ticker,
                    market=data.market,
                    asset_class=data.asset_class,
                ))
                logger.info(f"收藏 {data.ticker} 时自动注册品种（{data.asset_class}/{data.market}）")
            except Exception as e:
                # 唯一约束冲突 = 并发/重复注册，允许继续（收藏仍有效）
                logger.warning(f"自动注册品种冲突（忽略）: {e}")

        # 4. 幂等：按对齐后的三元组查自选（分类已统一，重复收藏必然命中）
        existing = await self._repo.get_watchlist(data.ticker, asset_class, market)
        if existing:
            return existing

        # 5. 写自选（对齐后的三元组 + 品种库名称快照）
        return await self._repo.create_watchlist(WatchlistCreate(
            ticker=data.ticker,
            asset_class=asset_class,
            market=market,
            name=name,
        ))

    async def delete_watchlist(self, watchlist_id: int) -> bool:
        """取消收藏（不影响品种库）"""
        return await self._repo.delete_watchlist(watchlist_id)

    async def list_with_quotes(self) -> list[WatchlistWithQuote]:
        """自选 + 实时行情（QuoteStatus 三态）

        复用 fetch_quote_map_concurrent：多组并发 + 超时熔断 + 单组容错 +
        失败降级 DB 历史。查无结果的 ticker 标记 UNAVAILABLE（不抛错，避免
        单只标的拉垮整个自选列表）。
        """
        items = await self._repo.list_watchlist()
        if not items:
            return []

        groups: dict[tuple[str, str], list[str]] = {}
        for it in items:
            groups.setdefault((it.asset_class, it.market), []).append(it.ticker)

        quote_map = await self._quote_svc.fetch_quote_map_concurrent(groups)

        result = []
        for it in items:
            entry = quote_map.get((it.asset_class, it.market, it.ticker))
            result.append(WatchlistWithQuote(
                id=it.id,
                ticker=it.ticker,
                asset_class=it.asset_class,
                market=it.market,
                name=it.name,
                quote=entry[0] if entry else None,
                status=entry[1] if entry else QuoteStatus.UNAVAILABLE,
            ))
        return result
