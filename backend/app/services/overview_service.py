"""概览业务逻辑 — 内部 USD 聚合，按 currency 参数换算返回"""

import asyncio
from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.models.overview import AllocationItem, OverviewStats
from app.repositories.asset_holding_repository import AssetHoldingRepository
from app.services.asset_quote_service import AssetQuoteService
from app.utils.exchange_rate import convert_with_rates, fetch_rates


class OverviewService:
    """概览统计业务逻辑"""

    def __init__(self):
        self._holding_repo = AssetHoldingRepository()
        self._quote_svc = AssetQuoteService()

    async def get_overview(self, currency: str = "CNY", force_refresh: bool = False) -> OverviewStats:
        """获取概览统计

        Args:
            currency: 显示币种（默认 CNY，可传 USD/HKD/EUR 等）
            force_refresh: True 时绕过基金 15 分钟缓存，强制拉取最新行情

        内部以 USD 为枢轴聚合，最后按 currency 换算返回。
        """
        holdings = await self._holding_repo.list_holdings()
        if not holdings:
            return OverviewStats(currency=currency)

        # 批量获取行情 — 各资产组并发拉取（超时熔断 + 单组容错），三元组 key 避免 ticker 冲突
        groups = defaultdict(list)
        for h in holdings:
            groups[(h.asset_class, h.market)].append(h.ticker)

        # 行情与汇率无依赖，并发拉取，避免串行累加耗时（行情最多 12s + 汇率最多 5s → 并发后取较大值）
        quote_map_task = asyncio.create_task(
            self._quote_svc.fetch_quote_map_concurrent(groups, force_refresh=force_refresh)
        )
        rate_snapshot_task = asyncio.create_task(fetch_rates())
        quote_map, rate_snapshot = await asyncio.gather(quote_map_task, rate_snapshot_task)
        rates = rate_snapshot.rates

        today = date.today()
        market_values_usd: dict[str, Decimal] = defaultdict(Decimal)

        # 构建逐只原始数据
        holdings_data = []
        for h in holdings:
            entry = quote_map.get((h.asset_class, h.market, h.ticker))
            current_price = float(entry[0].price) if entry else 0.0
            holdings_data.append({
                "current_price": current_price,
                "broker_cost_price": float(h.cost_price),
                "initial_buy_price": float(h.first_buy_price),
                "total_shares": float(h.quantity),
                "currency": h.currency,
            })
            # 配比用：累加各市场 USD 市值
            mv_usd = convert_with_rates(h.quantity * Decimal(str(current_price)), h.currency, "USD", rates)
            market_values_usd[h.market] += mv_usd

        # 调 formulas 统一计算组合盈亏
        from app.core.formulas import calculate_portfolio_overview
        result = calculate_portfolio_overview(holdings_data, {k: float(v) for k, v in rates.items()})

        total_value_usd = Decimal(str(result["total_value"]))
        total_cost_usd = Decimal(str(result["total_cost"]))
        total_pnl_usd = Decimal(str(result["net_profit"]))

        total_pnl_pct = result["rate_of_return"]
        if total_pnl_pct is None:
            total_pnl_pct = "+∞%"

        # 组合年化暂不计算
        avg_annualized: float | str | None = None

        # 按 currency 换算
        total_value = convert_with_rates(total_value_usd, "USD", currency, rates)
        total_cost = convert_with_rates(total_cost_usd, "USD", currency, rates)
        total_pnl = convert_with_rates(total_pnl_usd, "USD", currency, rates)

        # 资产配比（USD 算 pct，金额按 currency 换算）
        market_label = {"CN": "A 股", "US": "美股", "CRYPTO": "加密货币"}
        allocation = []
        for m, v_usd in sorted(market_values_usd.items(), key=lambda x: x[1], reverse=True):
            v_display = convert_with_rates(v_usd, "USD", currency, rates)
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
            rate_source_date=rate_snapshot.source_date,
            rate_stale=rate_snapshot.is_stale,
        )

