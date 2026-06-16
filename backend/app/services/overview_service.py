"""概览业务逻辑 — 内部 USD 聚合，按 currency 参数换算返回"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.models.overview import AllocationItem, OverviewStats
from app.repositories.asset_holding_repository import AssetHoldingRepository
from app.services.asset_quote_service import AssetQuoteService
from app.utils.exchange_rate import convert, to_usd


class OverviewService:
    """概览统计业务逻辑"""

    def __init__(self):
        self._holding_repo = AssetHoldingRepository()
        self._quote_svc = AssetQuoteService()

    async def get_overview(self, currency: str = "CNY") -> OverviewStats:
        """获取概览统计

        Args:
            currency: 显示币种（默认 CNY，可传 USD/HKD/EUR 等）

        内部以 USD 为枢轴聚合，最后按 currency 换算返回。
        """
        holdings = await self._holding_repo.list_holdings()
        if not holdings:
            return OverviewStats(currency=currency)

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
        total_value_usd = Decimal("0")
        total_cost_usd = Decimal("0")
        market_values_usd: dict[str, Decimal] = defaultdict(Decimal)

        for h in holdings:
            q = quote_map.get(h.ticker)
            current_price = q.price if q else Decimal("0")
            market_value = h.quantity * current_price

            mv_usd = await to_usd(market_value, h.currency)
            cost_usd = await to_usd(h.total_invested, h.currency)
            total_value_usd += mv_usd
            total_cost_usd += cost_usd
            market_values_usd[h.market] += mv_usd

        total_pnl_usd = total_value_usd - total_cost_usd

        # 总盈亏百分比（零成本兜底）
        total_pnl_pct: float | str | None = None
        if total_cost_usd > 0:
            total_pnl_pct = float((total_pnl_usd / total_cost_usd) * 100)
        elif total_cost_usd == 0 and total_value_usd > 0:
            total_pnl_pct = "+∞%"

        # 市值加权年化回报率
        has_inf = False
        weighted_return = Decimal("0")
        total_weight = Decimal("0")
        for h in holdings:
            q = quote_map.get(h.ticker)
            current_price = q.price if q else Decimal("0")
            mv_usd = await to_usd(h.quantity * current_price, h.currency)
            annualized = self._calc_annualized(current_price, h.cost_price, h.first_buy_date, today)
            if annualized == "+∞%":
                has_inf = True
            elif annualized is not None and mv_usd > 0:
                weighted_return += Decimal(str(annualized)) * mv_usd
                total_weight += mv_usd
        avg_annualized: float | str | None = None
        if has_inf:
            avg_annualized = "+∞%"
        elif total_weight > 0:
            avg_annualized = float(weighted_return / total_weight)

        # 按 currency 换算
        total_value = await convert(total_value_usd, "USD", currency)
        total_cost = await convert(total_cost_usd, "USD", currency)
        total_pnl = await convert(total_pnl_usd, "USD", currency)

        # 资产配比（USD 算 pct，金额按 currency 换算）
        market_label = {"CN": "A 股", "US": "美股", "CRYPTO": "加密货币"}
        allocation = []
        for m, v_usd in sorted(market_values_usd.items(), key=lambda x: x[1], reverse=True):
            v_display = await convert(v_usd, "USD", currency)
            pct = float((v_usd / total_value_usd) * 100) if total_value_usd > 0 else 0
            allocation.append(AllocationItem(
                market=m,
                label=market_label.get(m, m),
                value=v_display,
                pct=pct,
            ))

        return OverviewStats(
            currency=currency,
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            annualized_return=avg_annualized,
            allocation=allocation,
        )

    @staticmethod
    def _calc_annualized(
        current_price: Decimal, cost_price: Decimal, first_buy_date: date, today: date
    ) -> float | str | None:
        """计算简单年化回报率

        零成本持有（做T回本）时返回 "+∞%"
        """
        if not first_buy_date:
            return None
        if cost_price <= 0:
            return "+∞%" if current_price > 0 else None
        holding_days = (today - first_buy_date).days + 1
        if holding_days < 1:
            return None
        total_return_pct = float((current_price - cost_price) / cost_price) * 100
        return round(total_return_pct * (365 / holding_days), 4)
