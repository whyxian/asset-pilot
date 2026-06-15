"""概览业务逻辑"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessError
from app.models.asset_holding import AssetHolding
from app.models.overview import AllocationItem, OverviewStats
from app.repositories.asset_holding_repository import AssetHoldingRepository
from app.services.asset_quote_service import AssetQuoteService
from app.utils.exchange_rate import to_cny


class OverviewService:
    """概览统计业务逻辑"""

    def __init__(self):
        self._holding_repo = AssetHoldingRepository()
        self._quote_svc = AssetQuoteService()

    async def get_overview(self) -> OverviewStats:
        """获取概览统计（所有金额统一换算为 CNY）"""
        holdings = await self._holding_repo.list_holdings()
        if not holdings:
            return OverviewStats()

        # 批量获取行情
        groups = defaultdict(list)
        for h in holdings:
            groups[(h.asset_class, h.market)].append(h.ticker)

        quote_map = {}
        for (ac, market), tickers in groups.items():
            quotes = await self._quote_svc.fetch_quotes_by_asset_class(ac, market, tickers)
            for q in quotes:
                quote_map[q.ticker] = q

        today = date.today()
        total_value_cny = Decimal("0")
        total_cost_cny = Decimal("0")
        market_values: dict[str, Decimal] = defaultdict(Decimal)

        for h in holdings:
            q = quote_map.get(h.ticker)
            current_price = q.price if q else Decimal("0")
            market_value = h.quantity * current_price
            pnl = market_value - h.total_invested

            # 换算为 CNY
            mv_cny = await to_cny(market_value, h.currency)
            cost_cny = await to_cny(h.total_invested, h.currency)
            total_value_cny += mv_cny
            total_cost_cny += cost_cny
            market_values[h.market] += mv_cny

        total_pnl_cny = total_value_cny - total_cost_cny

        # 总盈亏百分比
        total_pnl_pct: float | str | None = None
        if total_cost_cny > 0:
            total_pnl_pct = float((total_pnl_cny / total_cost_cny) * 100)
        elif total_cost_cny == 0 and total_value_cny > 0:
            total_pnl_pct = "∞"  # 零成本持有

        # 市值加权年化回报率
        has_inf = False  # 是否有零成本持仓导致无穷大
        weighted_return = Decimal("0")
        total_weight = Decimal("0")
        for h in holdings:
            q = quote_map.get(h.ticker)
            current_price = q.price if q else Decimal("0")
            mv_cny = await to_cny(h.quantity * current_price, h.currency)
            annualized = self._calc_annualized(current_price, h.cost_price, h.first_buy_date, today)
            if annualized == "∞":
                has_inf = True
            elif annualized is not None and mv_cny > 0:
                weighted_return += Decimal(str(annualized)) * mv_cny
                total_weight += mv_cny
        avg_annualized: float | str | None = None
        if has_inf:
            avg_annualized = "∞"
        elif total_weight > 0:
            avg_annualized = float(weighted_return / total_weight)

        # 资产配比
        market_label = {"CN": "A 股", "US": "美股", "CRYPTO": "加密货币"}
        total = total_value_cny
        allocation = [
            AllocationItem(
                market=m,
                label=market_label.get(m, m),
                value_cny=v,
                pct=float((v / total) * 100) if total > 0 else 0,
            )
            for m, v in sorted(market_values.items(), key=lambda x: x[1], reverse=True)
        ]

        return OverviewStats(
            total_value_cny=total_value_cny,
            total_cost_cny=total_cost_cny,
            total_pnl_cny=total_pnl_cny,
            total_pnl_pct=total_pnl_pct,
            annualized_return=avg_annualized,
            allocation=allocation,
        )

    @staticmethod
    def _calc_annualized(
        current_price: Decimal, cost_price: Decimal, first_buy_date: date, today: date
    ) -> float | str | None:
        """计算简单年化回报率

        零成本持有（做T回本）时返回 "∞"
        """
        if not first_buy_date:
            return None
        if cost_price <= 0:
            return "∞" if current_price > 0 else None
        holding_days = (today - first_buy_date).days + 1
        if holding_days < 1:
            return None
        total_return_pct = float((current_price - cost_price) / cost_price) * 100
        return round(total_return_pct * (365 / holding_days), 4)
