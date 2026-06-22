"""快照业务逻辑 — 单事务写 networth + asset 两张表

设计要点：
- 一次 `take_snapshot()` 完成两张表的写入（单事务保证一致性）
- 当日重复调用会覆盖（INSERT OR REPLACE）
- 历史快照查询用快照里冻结的 fx_rates 换算（不用当前汇率）
"""

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.core.database import async_session
from app.core.logger import logger
from app.models.overview import AllocationItem
from app.models.snapshot import AssetSnapshot, NetWorthSnapshot
from app.repositories.asset_holding_repository import AssetHoldingRepository
from app.repositories.snapshot_repository import SnapshotRepository
from app.services.asset_quote_service import AssetQuoteService
from app.utils.exchange_rate import convert_with_rates, fetch_rates_snapshot


class SnapshotService:
    """快照业务"""

    def __init__(self):
        self._repo = SnapshotRepository()
        self._holding_repo = AssetHoldingRepository()
        self._quote_svc = AssetQuoteService()

    async def take_snapshot(
        self, snapshot_date: date | None = None
    ) -> NetWorthSnapshot:
        """记录当日快照（手动触发）

        单事务写两张表：networth_snapshots + asset_snapshots。
        当日已有快照会被覆盖。

        Args:
            snapshot_date: 默认今天；测试场景可指定日期
        """
        snap_date = snapshot_date or date.today()

        # 1. 拿当下完整汇率（USD-base，包含 CNY/HKD/EUR 等）
        rates = await fetch_rates_snapshot()

        # 2. 拿当下持仓 + 行情（各资产组并发拉取，超时熔断 + 单组容错）
        holdings = await self._holding_repo.list_holdings()
        groups = defaultdict(list)
        for h in holdings:
            groups[(h.asset_class, h.market)].append(h.ticker)

        quote_map = await self._quote_svc.fetch_quote_map_concurrent(groups)

        # 3. 算每只持仓的快照行（同时存原币和 USD）
        asset_rows = []
        market_values_usd: dict[str, Decimal] = defaultdict(Decimal)

        for h in holdings:
            entry = quote_map.get((h.asset_class, h.market, h.ticker))
            current_price = entry[0].price if entry else Decimal("0")
            market_value = h.quantity * current_price
            unrealized_pnl = market_value - h.total_invested

            mv_usd = convert_with_rates(market_value, h.currency, "USD", rates)
            cost_usd = convert_with_rates(h.total_invested, h.currency, "USD", rates)

            market_values_usd[h.market] += mv_usd

            # return_pct — 统一调 formulas.calculate_remaining_position_roi
            from app.core.formulas import calculate_remaining_position_roi

            return_pct: float | None = None
            result = calculate_remaining_position_roi(
                current_price=float(current_price),
                broker_cost_price=float(h.cost_price),
                initial_buy_price=float(h.first_buy_price),
                total_shares=float(h.quantity),
            )
            if result["success"]:
                return_pct = result["rate_of_return"]
            else:
                logger.warning(f"{h.ticker} 盈亏率计算失败: is_crazy_trader={result['is_crazy_trader']}")

            # 年化暂不计算
            annualized = None

            asset_rows.append({
                "snapshot_date": snap_date,
                "ticker": h.ticker,
                "asset_class": h.asset_class,
                "market": h.market,
                "name": h.name,
                "currency": h.currency,
                "quantity": h.quantity,
                "unit_value": current_price,
                "cost_value": h.cost_price,
                "first_buy_price": h.first_buy_price,
                "market_value": market_value,
                "market_value_usd": mv_usd,
                "total_invested": h.total_invested,
                "total_invested_usd": cost_usd,
                "unrealized_pnl": unrealized_pnl,
                "return_pct": Decimal(str(return_pct)) if return_pct is not None else None,
            })

        # 4. 算组合级聚合 — 调 formulas 统一计算
        from app.core.formulas import calculate_portfolio_overview
        portfolio = calculate_portfolio_overview(
            [{
                "current_price": float(r["unit_value"]),
                "broker_cost_price": float(r["cost_value"]),
                "initial_buy_price": float(r["first_buy_price"]),
                "total_shares": float(r["quantity"]),
                "currency": r["currency"],
            } for r in asset_rows],
            {k: float(v) for k, v in rates.items()},
        )
        total_value_usd = Decimal(str(portfolio["total_value"]))
        total_cost_usd = Decimal(str(portfolio["total_cost"]))
        total_pnl_usd = Decimal(str(portfolio["net_profit"]))

        total_pnl_pct: Decimal | None = None
        if portfolio["rate_of_return"] is not None:
            total_pnl_pct = Decimal(str(portfolio["rate_of_return"]))
        # rate_of_return=None（零成本/负成本）→ DB 存 NULL，前端展示 "+∞%"

        # 年化暂不计算
        annualized_return: Decimal | None = None

        # 配比（USD 计算 pct，存 USD 值）
        market_label = {"CN": "A 股", "US": "美股", "CRYPTO": "加密货币"}
        allocation_data = []
        for m, v_usd in sorted(market_values_usd.items(), key=lambda x: x[1], reverse=True):
            pct = float((v_usd / total_value_usd) * 100) if total_value_usd > 0 else 0
            allocation_data.append({
                "market": m,
                "label": market_label.get(m, m),
                "value_usd": str(v_usd),  # JSON 中用 str 存 Decimal
                "pct": pct,
            })

        networth_data = {
            "snapshot_date": snap_date,
            "total_value_usd": total_value_usd,
            "total_cost_usd": total_cost_usd,
            "total_pnl_usd": total_pnl_usd,
            "total_pnl_pct": total_pnl_pct,
            "annualized_return": annualized_return,
            "allocation": json.dumps(allocation_data),
            "fx_rates": json.dumps(rates),
        }

        # 5. 单事务写两张表
        async with async_session() as session:
            try:
                await self._repo.upsert_networth_snapshot(session, networth_data)
                await self._repo.upsert_asset_snapshots(session, asset_rows)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

        logger.info(f"快照已记录：{snap_date}，{len(asset_rows)} 只持仓")

        # 6. 返回组合快照（按 USD 返回，调用方可改用 list_snapshots 查 CNY 视图）
        return NetWorthSnapshot(
            snapshot_date=snap_date,
            currency="USD",
            total_value=total_value_usd,
            total_cost=total_cost_usd,
            total_pnl=total_pnl_usd,
            total_pnl_pct=float(total_pnl_pct) if total_pnl_pct is not None else (
                "+∞%" if total_cost_usd == 0 and total_value_usd > 0 else None
            ),
            annualized_return=float(annualized_return) if annualized_return is not None else None,
            allocation=[
                AllocationItem(
                    market=a["market"], label=a["label"],
                    value=Decimal(a["value_usd"]), pct=a["pct"],
                )
                for a in allocation_data
            ],
        )

    async def list_snapshots(
        self, currency: str = "CNY", limit: int = 365
    ) -> list[NetWorthSnapshot]:
        """读组合级快照（按 currency 用快照里冻结的 fx_rates 换算）

        历史曲线反映"那一刻"的目标币种价值。
        """
        records = await self._repo.list_networth_snapshots(limit=limit)
        results = []
        for r in records:
            rates = json.loads(r.fx_rates) if r.fx_rates else {}
            allocation_raw = json.loads(r.allocation) if r.allocation else []

            total_value = convert_with_rates(
                Decimal(str(r.total_value_usd)), "USD", currency, rates,
            )
            total_cost = convert_with_rates(
                Decimal(str(r.total_cost_usd)), "USD", currency, rates,
            )
            total_pnl = convert_with_rates(
                Decimal(str(r.total_pnl_usd)), "USD", currency, rates,
            )

            # 还原 +∞% 显示（DB 存的是 NULL，但当时实际是零成本）
            pnl_pct: float | str | None = (
                float(r.total_pnl_pct) if r.total_pnl_pct is not None
                else ("+∞%" if r.total_cost_usd == 0 and r.total_value_usd > 0 else None)
            )
            ann: float | str | None = (
                float(r.annualized_return) if r.annualized_return is not None
                else None  # 历史无法判定 has_inf，保持 None
            )

            allocation = [
                AllocationItem(
                    market=a["market"], label=a["label"],
                    value=convert_with_rates(Decimal(a["value_usd"]), "USD", currency, rates),
                    pct=a["pct"],
                )
                for a in allocation_raw
            ]

            results.append(NetWorthSnapshot(
                snapshot_date=r.snapshot_date,
                currency=currency,
                total_value=total_value,
                total_cost=total_cost,
                total_pnl=total_pnl,
                total_pnl_pct=pnl_pct,
                annualized_return=ann,
                allocation=allocation,
            ))
        return results

    async def list_asset_snapshots(
        self,
        currency: str = "CNY",
        ticker: str | None = None,
        asset_class: str | None = None,
        market: str | None = None,
        limit: int = 365,
    ) -> list[AssetSnapshot]:
        """读品种级快照（按 currency 换算 market_value_in_currency / total_invested_in_currency）

        换算用快照所在日的 fx_rates（需要联查 networth_snapshots，
        但当前简化为"用当前汇率"，未来若品种级也要历史 FX 再扩展）。

        Note:
            原币字段（unit_value/cost_value/market_value/unrealized_pnl）始终原样返回。
        """
        records = await self._repo.list_asset_snapshots(
            ticker=ticker, asset_class=asset_class, market=market, limit=limit,
        )
        # 联查同日 networth 的 fx_rates 做精确历史换算
        # 简化：先按 USD 列直接读，前端按需换算
        results = []
        for r in records:
            mv_usd = Decimal(str(r.market_value_usd))
            ti_usd = Decimal(str(r.total_invested_usd))

            # 简化策略：用当前汇率（品种级回看精度要求较低）
            from app.utils.exchange_rate import convert
            mv_in_ccy = await convert(mv_usd, "USD", currency)
            ti_in_ccy = await convert(ti_usd, "USD", currency)

            results.append(AssetSnapshot(
                snapshot_date=r.snapshot_date,
                ticker=r.ticker,
                asset_class=r.asset_class,
                market=r.market,
                name=r.name,
                currency=r.currency,
                quantity=Decimal(str(r.quantity)),
                unit_value=Decimal(str(r.unit_value)),
                cost_value=Decimal(str(r.cost_value)),
                market_value=Decimal(str(r.market_value)),
                total_invested=Decimal(str(r.total_invested)),
                unrealized_pnl=Decimal(str(r.unrealized_pnl)),
                return_pct=float(r.return_pct) if r.return_pct is not None else None,
                display_currency=currency,
                market_value_in_currency=mv_in_ccy,
                total_invested_in_currency=ti_in_ccy,
            ))
        return results
