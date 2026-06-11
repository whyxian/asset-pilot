"""持仓业务逻辑"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessError
from app.models.asset_holding import AssetHolding, AssetHoldingCreate, AssetHoldingUpdate, HoldingWithQuote
from app.repositories.asset_holding_repository import AssetHoldingRepository
from app.repositories.asset_variety_repository import AssetVarietyRepository
from app.services.asset_quote_service import AssetQuoteService


class AssetHoldingService:
    """持仓业务逻辑"""

    def __init__(self):
        self._repo = AssetHoldingRepository()
        self._variety_repo = AssetVarietyRepository()
        self._quote_svc = AssetQuoteService()

    async def list_holdings(self) -> list[AssetHolding]:
        """获取全部持仓"""
        return await self._repo.list_holdings()

    async def get_holding(self, ticker: str) -> AssetHolding | None:
        """按代码获取持仓"""
        return await self._repo.get_holding(ticker)

    async def create_holding(self, data: AssetHoldingCreate) -> AssetHolding:
        """新增持仓（校验品种是否存在，名称空时从品种记录自动补填）"""
        variety = await self._variety_repo.get_variety(data.ticker, data.asset_class, data.market)
        if not variety:
            raise BusinessError(40001, f"未识别的品种代码 '{data.ticker}'，请先通过 /api/v1/varieties 添加该品种")
        # 前端可能未传 name，从品种记录补填
        if not data.name:
            data = data.model_copy(update={"name": variety.name})
        return await self._repo.create_holding(data)

    async def update_holding(self, ticker: str, data: AssetHoldingUpdate) -> AssetHolding | None:
        """更新持仓"""
        return await self._repo.update_holding(ticker, data)

    async def delete_holding(self, ticker: str) -> bool:
        """删除持仓"""
        return await self._repo.delete_holding(ticker)

    async def list_holdings_with_quotes(self) -> list[HoldingWithQuote]:
        """获取持仓列表，合并实时行情并计算市值/盈亏/年化

        Returns:
            带实时行情的持仓列表
        """
        holdings = await self._repo.list_holdings()
        if not holdings:
            return []

        # 按 (asset_class, market) 分组，批量获取行情
        groups = defaultdict(list)
        for h in holdings:
            groups[(h.asset_class, h.market)].append(h.ticker)

        quote_map = {}
        for (ac, market), tickers in groups.items():
            if ac == "STOCK":
                quotes = await self._quote_svc.fetch_stock_quotes(market, tickers)
            elif ac == "FUND":
                quotes = await self._quote_svc.fetch_fund_quotes(market, tickers)
            else:
                quotes = []
            for q in quotes:
                quote_map[q.ticker] = q

        today = date.today()
        results = []
        for h in holdings:
            q = quote_map.get(h.ticker)
            current_price = q.price if q else Decimal("0")
            market_value = h.quantity * current_price
            pnl = market_value - h.total_invested

            # 盈亏百分比
            pnl_pct = None
            if h.total_invested > 0:
                pnl_pct = float((pnl / h.total_invested) * 100)

            # 简单年化回报率 = 总收益率 × (365 / 持有天数)
            # 持有天数 = (今日 - 首次买入日) + 1，当天买入也算持有 1 天
            annualized = None
            if h.cost_price > 0 and h.first_buy_date:
                holding_days = (today - h.first_buy_date).days + 1
                if holding_days >= 1:
                    total_return_pct = float((current_price - h.cost_price) / h.cost_price) * 100
                    annualized = round(total_return_pct * (365 / holding_days), 4)

            results.append(HoldingWithQuote(
                ticker=h.ticker,
                name=h.name,
                market=h.market,
                asset_class=h.asset_class,
                currency=h.currency,
                quantity=h.quantity,
                cost_price=h.cost_price,
                total_invested=h.total_invested,
                first_buy_date=h.first_buy_date,
                current_price=current_price,
                market_value=market_value,
                pnl=pnl,
                pnl_pct=pnl_pct,
                annualized_return=annualized,
            ))

        return results
