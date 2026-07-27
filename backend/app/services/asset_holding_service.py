"""持仓业务逻辑

数据约束：(asset_class, market, ticker) 三元组唯一定位一笔持仓。
所有按品种操作的函数都必须传完整三元组。
"""

import asyncio
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.core.logger import logger
from app.models.asset_holding import (
    AssetHolding,
    AssetHoldingCreate,
    AssetHoldingUpdate,
    HoldingsWithQuotesResponse,
    HoldingWithQuote,
    MarketSummary,
)
from app.models.asset_quote import AssetQuote, QuoteStatus
from app.models.orm.asset_holding_orm import AssetHoldingRecord
from app.models.orm.transaction_orm import TransactionRecord
from app.repositories.asset_holding_repository import AssetHoldingRepository, _record_to_holding
from app.repositories.asset_variety_repository import AssetVarietyRepository
from app.services.asset_quote_service import AssetQuoteService
from app.utils.exchange_rate import convert_with_rates, fetch_rates


class AssetHoldingService:
    """持仓业务逻辑"""

    def __init__(self):
        self._repo = AssetHoldingRepository()
        self._variety_repo = AssetVarietyRepository()
        self._quote_svc = AssetQuoteService()

    async def list_holdings(self) -> list[AssetHolding]:
        """获取全部持仓"""
        return await self._repo.list_holdings()

    async def get_holding(
        self, ticker: str, asset_class: str, market: str
    ) -> AssetHolding | None:
        """按三元组获取持仓"""
        return await self._repo.get_holding(ticker, asset_class, market)

    async def create_holding(self, data: AssetHoldingCreate) -> HoldingWithQuote:
        """新增持仓（建仓 = 拉行情校验 + 写持仓行 + 生成建仓 buy 交易 + recompute）

        业务约束：建仓时必须能拉到该 ticker 的实时行情，拉不到则建仓失败。
        建仓自动生成一笔 buy 交易（用建仓表单的 quantity/cost_price/total_invested），
        交易记录成为唯一现金流事实源（为 XIRR 铺路）。initial_* 已废弃，派生字段由
        recompute 从 0 起点回放交易算出。事务原子：行情校验 → 持仓 + 交易 + recompute。
        """
        from app.core.database import async_session
        from decimal import Decimal as _D

        # 0. 校验 total_invested == quantity × cost_price（不信任前端）
        expected = _D(str(data.quantity)) * _D(str(data.cost_price))
        actual = _D(str(data.total_invested))
        if abs(expected - actual) > _D("0.01"):
            raise BusinessError(
                40001,
                f"总投入与 数量×成本价 不一致：期望 {expected}，实际 {actual}",
            )

        # 1. 校验品种存在
        variety = await self._variety_repo.get_variety(data.ticker, data.asset_class, data.market)
        if not variety:
            raise BusinessError(40001, f"未识别的品种代码 '{data.ticker}'，请先通过 /api/v1/varieties 添加该品种")

        # 2. 拉取该 ticker 行情（先拉后建仓，失败直接抛错不写 DB；同时预热缓存）
        quotes = await self._quote_svc.fetch_quotes_by_asset_class(
            data.asset_class, data.market, [data.ticker],
        )
        quote = next((q for q in quotes if q.ticker == data.ticker), None)
        if quote is None:
            raise BusinessError(
                40002,
                f"无法获取 '{data.ticker}' 的实时行情，请检查代码是否正确或稍后重试",
            )

        # 3. 名称补填：行情名优先，其次品种记录名
        if not data.name:
            name = quote.name or variety.name
            data = data.model_copy(update={"name": name})

        # 4. 事务：建仓行 + 建仓 buy 交易 + recompute
        async with async_session() as session:
            try:
                record = AssetHoldingRecord(
                    ticker=data.ticker,
                    name=data.name,
                    market=data.market,
                    asset_class=data.asset_class,
                    currency=data.currency,
                    quantity=data.quantity,
                    cost_price=data.cost_price,
                    total_invested=data.total_invested,
                    first_buy_date=data.first_buy_date,
                    first_buy_price=data.cost_price,  # 建仓首笔买入价（盈亏率公式分母，不变）
                    cash_account_enabled=data.cash_account_enabled,
                )
                session.add(record)
                await session.flush()

                # 建仓 buy 交易（用建仓表单数据）
                txn = TransactionRecord(
                    ticker=data.ticker,
                    asset_class=data.asset_class,
                    market=data.market,
                    transaction_date=data.first_buy_date,
                    type="buy",
                    quantity=data.quantity,
                    unit_price=data.cost_price,
                    amount=data.total_invested,
                    notes="建仓",
                )
                session.add(txn)
                await session.flush()

                # recompute 从 0 起点回放这笔建仓交易 → 派生字段正确
                await recompute_holding(session, data.ticker, data.asset_class, data.market)

                # 现金账户联动：如果开启了现金，建仓 buy 从现金扣款
                if data.cash_account_enabled and data.total_invested:
                    from app.models.orm.cash_flow_orm import CashFlowRecord
                    from sqlalchemy import func
                    from decimal import Decimal as _C
                    # 校验余额
                    balance = (await session.execute(
                        select(func.coalesce(func.sum(CashFlowRecord.amount), 0))
                        .where(CashFlowRecord.currency == data.currency)
                    )).scalar()
                    balance = _C(str(balance))
                    invested = _C(str(data.total_invested))
                    if balance < invested:
                        raise BusinessError(40001,
                            f"{data.currency} 现金余额不足：当前 {balance}，需要 {invested}")
                    session.add(CashFlowRecord(
                        type="buy", amount=-invested, currency=data.currency,
                        transaction_id=txn.id, notes=f"建仓 {data.ticker} 扣款",
                    ))

                await session.commit()
                await session.refresh(record)
                holding = _record_to_holding(record)
            except Exception:
                await session.rollback()
                raise

        # 5. 返回带行情的 HoldingWithQuote
        return self._build_holding_with_quote(holding, (quote, QuoteStatus.REALTIME), date.today())

    async def update_holding(
        self, ticker: str, asset_class: str, market: str, data: AssetHoldingUpdate
    ) -> AssetHolding | None:
        """更新持仓 — name 直接改；现金流字段(quantity/cost_price/total_invested)生成勘误交易

        勘误交易日期 = 持仓的 first_buy_date（并到建仓时点，XIRR 影响最小）：
        - 改份额：差额=新-旧，正→buy(差额股,unit_price=旧cost_price)，负→sell(|差额|,unit_price=旧cost_price)
        - 改成本(份额不变)：差额=新total_invested-旧，生成 quantity=0 amount=差额 的 buy（补记额外投入）
        first_buy_date 不允许改（由建仓交易决定）。
        """
        from app.core.database import async_session

        update_dict = data.model_dump(exclude_unset=True)
        has_cashflow = any(k in update_dict for k in ("quantity", "cost_price", "total_invested"))

        # 非现金流字段（name）直接走 repo 更新
        if not has_cashflow:
            return await self._repo.update_holding(ticker, asset_class, market, data)

        # 现金流字段：生成勘误交易 + recompute（事务原子）
        async with async_session() as session:
            try:
                holding = await self._repo.get_record_in_session(session, ticker, asset_class, market)
                if holding is None:
                    return None

                old_qty = Decimal(str(holding.quantity))
                old_cost = Decimal(str(holding.cost_price))
                old_total = Decimal(str(holding.total_invested))
                new_qty = Decimal(str(update_dict["quantity"])) if "quantity" in update_dict and update_dict["quantity"] is not None else old_qty
                new_total = Decimal(str(update_dict["total_invested"])) if "total_invested" in update_dict and update_dict["total_invested"] is not None else old_total

                # name 等非现金流字段同步改
                if update_dict.get("name") is not None:
                    holding.name = update_dict["name"]

                qty_diff = new_qty - old_qty
                total_diff = new_total - old_total
                txn_date = holding.first_buy_date

                if qty_diff != 0:
                    # 改份额：差额生成 buy/sell
                    txn_type = "buy" if qty_diff > 0 else "sell"
                    abs_qty = abs(qty_diff)
                    txn = TransactionRecord(
                        ticker=ticker, asset_class=asset_class, market=market,
                        transaction_date=txn_date, type=txn_type,
                        quantity=abs_qty, unit_price=old_cost,
                        amount=abs_qty * old_cost,
                        notes=f"手动调整:份额 {old_qty}→{new_qty}",
                    )
                    session.add(txn)
                elif total_diff != 0:
                    # 改成本(份额不变)：quantity=0 amount=差额
                    txn = TransactionRecord(
                        ticker=ticker, asset_class=asset_class, market=market,
                        transaction_date=txn_date, type="buy",
                        quantity=Decimal("0"), unit_price=None,
                        amount=total_diff,
                        notes=f"手动调整:成本 {old_total}→{new_total}",
                    )
                    session.add(txn)

                await session.flush()
                await recompute_holding(session, ticker, asset_class, market)
                await session.commit()
                await session.refresh(holding)
                return _record_to_holding(holding)
            except Exception:
                await session.rollback()
                raise

    async def delete_holding(
        self, ticker: str, asset_class: str, market: str
    ) -> int:
        """删除持仓 — 级联删除该品种的全部关联交易记录（事务原子）

        Returns:
            一并删除的关联交易记录条数；持仓本身不存在时返回 -1
        """
        from app.core.database import async_session
        async with async_session() as session:
            try:
                # 先确认持仓存在
                holding = await self._repo.get_record_in_session(session, ticker, asset_class, market)
                if holding is None:
                    return -1

                # 删除该品种(三元组定位)的全部交易
                txn_records = (await session.execute(
                    select(TransactionRecord).where(
                        TransactionRecord.ticker == ticker,
                        TransactionRecord.asset_class == asset_class,
                        TransactionRecord.market == market,
                    )
                )).scalars().all()
                txn_count = len(txn_records)
                for t in txn_records:
                    await session.delete(t)

                # 再删持仓
                await session.delete(holding)
                await session.commit()
                return txn_count
            except Exception:
                await session.rollback()
                raise

    async def list_holdings_with_quotes(
        self, force_refresh: bool = False
    ) -> HoldingsWithQuotesResponse:
        """获取持仓列表 + 市场汇总，合并实时行情并计算市值/盈亏/年化

        Args:
            force_refresh: True 时绕过基金 15 分钟缓存，强制拉取最新行情

        Returns:
            HoldingsWithQuotesResponse（holdings 持仓列表 + market_summary 各市场 USD 市值占比）
        """
        holdings = await self._repo.list_holdings()
        if not holdings:
            return HoldingsWithQuotesResponse()

        # 按 (asset_class, market) 分组，批量获取行情（已清仓品种 quantity=0 也参与，便于前端展示历史价格）
        groups = defaultdict(list)
        for h in holdings:
            groups[(h.asset_class, h.market)].append(h.ticker)

        # 行情与汇率无依赖，并发拉取（fetch_rates 有缓存+单飞，命中时几乎无开销）
        quote_map_task = asyncio.create_task(
            self._quote_svc.fetch_quote_map_concurrent(groups, force_refresh=force_refresh)
        )
        rate_snapshot_task = asyncio.create_task(fetch_rates())
        quote_map, rate_snapshot = await asyncio.gather(quote_map_task, rate_snapshot_task)
        rates = rate_snapshot.rates

        today = date.today()
        results = []
        # 各市场 USD 市值累加，用于 market_summary 占比
        market_value_usd_by_market: dict[str, Decimal] = defaultdict(Decimal)
        for h in holdings:
            q = quote_map.get((h.asset_class, h.market, h.ticker))
            hwq = self._build_holding_with_quote(h, q, today)
            market_value_usd_by_market[h.market] += convert_with_rates(
                hwq.market_value, h.currency, "USD", rates
            )
            results.append(hwq)

        # 市场汇总：按市场聚合 USD 市值，算占比（市值降序排列）
        market_label = {"CN": "A 股", "US": "美股", "CRYPTO": "加密货币"}
        total_value_usd = sum(market_value_usd_by_market.values(), Decimal("0"))
        market_summary = []
        for market, value_usd in sorted(
            market_value_usd_by_market.items(), key=lambda x: x[1], reverse=True
        ):
            count = sum(1 for h in holdings if h.market == market)
            pct = float((value_usd / total_value_usd) * 100) if total_value_usd > 0 else 0.0
            market_summary.append(MarketSummary(
                market=market,
                label=market_label.get(market, market),
                count=count,
                value_usd=value_usd,
                pct=round(pct, 2),
            ))

        return HoldingsWithQuotesResponse(holdings=results, market_summary=market_summary)

    @staticmethod
    def _build_holding_with_quote(
        h: AssetHolding,
        q_with_status: tuple[AssetQuote, QuoteStatus] | None,
        today: date,
    ) -> HoldingWithQuote:
        """单条持仓 + 行情 → HoldingWithQuote（算现价/市值/盈亏/年化 + 透传状态）

        供建仓返回和列表聚合复用。行情缺失（None）时现价兜底 0 + 状态 UNAVAILABLE。

        Args:
            h: 持仓基线
            q_with_status: (行情, 状态)，None 时现价按 0、状态 UNAVAILABLE
            today: 今日（算年化用）

        Returns:
            带实时计算字段 + quote_status 的 HoldingWithQuote
        """
        if q_with_status is None:
            current_price = Decimal("0")
            quote_status = QuoteStatus.UNAVAILABLE.value
        else:
            q, status = q_with_status
            current_price = q.price
            quote_status = status.value
        market_value = h.quantity * current_price
        pnl = market_value - h.total_invested

        # 盈亏率 — 统一调 formulas.calculate_remaining_position_roi
        from app.core.formulas import calculate_remaining_position_roi

        pnl_pct: float | str | None = None
        result = calculate_remaining_position_roi(
            current_price=current_price,
            broker_cost_price=h.cost_price,
            initial_buy_price=h.first_buy_price,
            total_shares=h.quantity,
        )
        if result["success"]:
            pnl_pct = result["rate_of_return"]
        else:
            # 计算失败（如首买价=0 脏数据或除零异常），保持 None，前端显示 N/A
            logger.warning(f"{h.ticker} 盈亏率计算失败: is_crazy_trader={result['is_crazy_trader']}")

        # 年化回报暂不计算
        annualized = None

        return HoldingWithQuote(
            ticker=h.ticker,
            name=h.name,
            market=h.market,
            asset_class=h.asset_class,
            currency=h.currency,
            quantity=h.quantity,
            cost_price=h.cost_price,
            total_invested=h.total_invested,
            first_buy_date=h.first_buy_date,
            first_buy_price=h.first_buy_price,
            liquidated_at=h.liquidated_at,
            current_price=current_price,
            market_value=market_value,
            pnl=pnl,
            pnl_pct=pnl_pct,
            annualized_return=annualized,
            quote_status=quote_status,
        )


async def recompute_holding(
    session: AsyncSession, ticker: str, asset_class: str, market: str
) -> None:
    """全量重算指定品种的派生持仓字段（quantity / cost_price / total_invested / liquidated_at）

    算法：
        1. 从 0 起点（q=0, p=0, t=0）开始——交易记录是唯一事实源，
           建仓那笔 buy 交易已包含在交易记录里，不再用 initial_* 基线。
        2. 按 (transaction_date 升序, id 升序) 顺序回放该品种全部交易（三元组过滤）：
           - buy:  amt = transaction.amount 优先，否则 quantity * unit_price
                   new_q = q + qty
                   new_t = t + amt
                   new_p = new_t / new_q
           - sell: 降低成本法 — sell 的"成交金额"冲减 total_invested
                   if qty > q: 抛出 BusinessError "卖超"
                   new_q = q - qty
                   new_t = max(t - sell_price × qty, 0)   # 下限 0
                   new_p = new_t / new_q (清仓时归零)
        3. 写回 holdings 派生字段。
        4. 最终 q == 0：liquidated_at = 最后一笔 sell 的日期（短暂中间态，
           调用方在事务内调用 archive_holding 后该行就会被搬走）；
           最终 q > 0：liquidated_at = None。

    注：自从引入 closed_holdings 归档机制后，"清仓后再 buy 复活"的场景
    不会再发生（清仓 → 立即归档 → holdings 中无此品种 → 再交易会被
    "必须先建仓"校验拦下）。所以本函数不再处理复活逻辑。

    Args:
        session: 外部传入的 session（必须由调用方控制 commit/rollback）
        ticker, asset_class, market: 三元组定位品种

    Raises:
        BusinessError: holdings 中不存在该品种，或某笔 sell 卖超
    """
    from app.repositories.asset_holding_repository import AssetHoldingRepository
    repo = AssetHoldingRepository()

    # 取持仓 ORM 记录（按三元组）
    holding = await repo.get_record_in_session(session, ticker, asset_class, market)
    if holding is None:
        raise BusinessError(40401, f"持仓 '{ticker}' ({asset_class}/{market}) 不存在，无法重算")

    # 起点 = 0（交易记录是唯一事实源，建仓 buy 交易已含在内）
    q = Decimal("0")
    p = Decimal("0")
    t = Decimal("0")

    # 按时间正序回放该品种的全部交易（三元组过滤，避免不同品种同 ticker 串扰）
    txns = (await session.execute(
        select(TransactionRecord)
        .where(
            TransactionRecord.ticker == ticker,
            TransactionRecord.asset_class == asset_class,
            TransactionRecord.market == market,
        )
        .order_by(TransactionRecord.transaction_date.asc(), TransactionRecord.id.asc())
    )).scalars().all()

    for txn in txns:
        if txn.type == "buy":
            qty = Decimal(str(txn.quantity)) if txn.quantity is not None else Decimal("0")
            # amount 优先，其次 quantity * unit_price
            if txn.amount is not None:
                amt = Decimal(str(txn.amount))
            elif txn.quantity is not None and txn.unit_price is not None:
                amt = Decimal(str(txn.quantity)) * Decimal(str(txn.unit_price))
            else:
                amt = Decimal("0")
            q = q + qty
            t = t + amt
            p = (t / q) if q > 0 else Decimal("0")

        elif txn.type == "sell":
            if txn.quantity is None:
                raise BusinessError(40001, f"卖出交易 #{txn.id} 缺少数量字段")
            qty = Decimal(str(txn.quantity))
            if qty > q:
                raise BusinessError(
                    40001,
                    f"卖出 {qty} 超过当前持仓 {q}（交易 #{txn.id}，{txn.transaction_date}）",
                )
            # 降低成本法（适配做 T）：sell 的"成交金额"直接冲减总成本
            # 推导 sell_price：unit_price 优先；否则 amount / quantity；都无则退化为 cost_price（差额=0）
            if txn.unit_price is not None:
                sell_price = Decimal(str(txn.unit_price))
            elif txn.amount is not None and qty > 0:
                sell_price = Decimal(str(txn.amount)) / qty
            else:
                sell_price = p

            q = q - qty
            t = t - sell_price * qty
            # 允许 t 为负：做 T 累计赚的超过总投入时，成本为负表示「已落袋的赠送市值」

            if q == 0:
                p = Decimal("0")
                t = Decimal("0")  # 清仓后总投入归零
            else:
                p = t / q  # 重算成本价
        else:
            raise BusinessError(40001, f"未知交易类型 '{txn.type}'（交易 #{txn.id}）")

    # 写回派生字段
    holding.quantity = q
    holding.cost_price = p
    holding.total_invested = t

    # 标记清仓日期（短暂中间态，下一步 archive_holding 会把整行搬走）
    if q == 0:
        last_sell = next((x for x in reversed(txns) if x.type == "sell"), None)
        holding.liquidated_at = last_sell.transaction_date if last_sell else None
    else:
        holding.liquidated_at = None

    # session.commit() 由调用方负责


async def archive_holding(
    session: AsyncSession, ticker: str, asset_class: str, market: str
) -> int:
    """把 quantity=0 的持仓归档到 closed_holdings + closed_transactions，并删除原表对应记录。

    调用方负责 commit / rollback。

    Args:
        session: 外部 session
        ticker, asset_class, market: 三元组定位品种

    Returns:
        新建的 closed_holding.id

    Raises:
        BusinessError: 持仓不存在 / quantity != 0
    """
    from app.models.orm.closed_holding_orm import ClosedHoldingRecord, ClosedTransactionRecord
    from app.repositories.asset_holding_repository import AssetHoldingRepository
    repo = AssetHoldingRepository()

    holding = await repo.get_record_in_session(session, ticker, asset_class, market)
    if holding is None:
        raise BusinessError(40401, f"持仓 '{ticker}' ({asset_class}/{market}) 不存在，无法归档")
    if Decimal(str(holding.quantity)) != Decimal("0"):
        raise BusinessError(40001, f"持仓 '{ticker}' quantity={holding.quantity} 非 0，不能归档")

    txns = (await session.execute(
        select(TransactionRecord)
        .where(
            TransactionRecord.ticker == ticker,
            TransactionRecord.asset_class == asset_class,
            TransactionRecord.market == market,
        )
        .order_by(TransactionRecord.transaction_date.asc(), TransactionRecord.id.asc())
    )).scalars().all()

    # 计算 realized_pnl = sum(sell.amount) - sum(buy.amount)
    # 建仓投入通过 buy 交易体现（initial_* 已废弃）
    sum_buy = Decimal("0")
    sum_sell = Decimal("0")
    for txn in txns:
        # 取金额：amount 优先，其次 quantity * unit_price
        if txn.amount is not None:
            amt = Decimal(str(txn.amount))
        elif txn.quantity is not None and txn.unit_price is not None:
            amt = Decimal(str(txn.quantity)) * Decimal(str(txn.unit_price))
        else:
            amt = Decimal("0")
        if txn.type == "buy":
            sum_buy += amt
        elif txn.type == "sell":
            sum_sell += amt

    realized_pnl = sum_sell - sum_buy

    # 清仓日期：取 holdings 当前 liquidated_at（recompute 刚写好）；兜底用最后一笔 sell 日期
    closed_at = holding.liquidated_at
    if closed_at is None:
        last_sell = next((x for x in reversed(txns) if x.type == "sell"), None)
        if last_sell is None:
            raise BusinessError(40001, f"持仓 '{ticker}' 没有清仓日期，无法归档")
        closed_at = last_sell.transaction_date

    holding_days = (closed_at - holding.first_buy_date).days + 1

    # Modified Dietz：建仓当 V0，最后一笔卖出当 V1，其余当现金流
    from app.core.formulas import calculate_modified_dietz
    # 建仓交易：按时间正序第一条 buy（建仓时 notes="建仓"）
    first_buy = next((x for x in txns if x.type == "buy"), None)
    v0_amount = Decimal("0")
    # 最后一笔卖出
    last_sell = next((x for x in reversed(txns) if x.type == "sell"), None)
    v1_amount = Decimal("0")
    trade_flows = []

    def _resolve_amt(txn) -> Decimal:
        if txn.amount is not None:
            return Decimal(str(txn.amount))
        if txn.quantity is not None and txn.unit_price is not None:
            return Decimal(str(txn.quantity)) * Decimal(str(txn.unit_price))
        return Decimal("0")

    for txn in txns:
        if txn is first_buy:
            v0_amount = _resolve_amt(txn)
            continue
        if txn is last_sell:
            v1_amount = _resolve_amt(txn)
            continue
        amt_val = _resolve_amt(txn)
        flow_amt = amt_val if txn.type == "buy" else -amt_val
        trade_flows.append({"date": str(txn.transaction_date), "amount": flow_amt})

    dietz_result = calculate_modified_dietz(
        V0=v0_amount,
        V1=v1_amount,
        trade_flows=trade_flows,
        start_date=str(holding.first_buy_date),
        end_date=str(closed_at),
    )
    # pnl_pct 存 float→Decimal；is_crazy_trader 直接用
    dietz_pnl = dietz_result["rate_of_return"]
    pnl_pct = Decimal(str(dietz_pnl)).quantize(Decimal("0.01")) if dietz_pnl is not None else None
    is_crazy_trader = dietz_result["is_crazy_trader"]

    # INSERT closed_holdings
    closed = ClosedHoldingRecord(
        ticker=holding.ticker,
        name=holding.name,
        market=holding.market,
        asset_class=holding.asset_class,
        currency=holding.currency,
        total_buy_amount=sum_buy,
        first_buy_date=holding.first_buy_date,
        first_buy_price=holding.first_buy_price,
        closed_at=closed_at,
        holding_days=holding_days,
        realized_pnl=realized_pnl,
        pnl_pct=pnl_pct,
        is_crazy_trader=is_crazy_trader,
    )
    session.add(closed)
    await session.flush()  # 拿 closed.id

    # INSERT closed_transactions（关联到 closed.id；带上品种三元组）
    for txn in txns:
        session.add(ClosedTransactionRecord(
            closed_holding_id=closed.id,
            ticker=txn.ticker,
            asset_class=txn.asset_class,
            market=txn.market,
            transaction_date=txn.transaction_date,
            type=txn.type,
            quantity=txn.quantity,
            unit_price=txn.unit_price,
            amount=txn.amount,
            fee_rate=txn.fee_rate,
            notes=txn.notes,
            original_id=txn.id,
        ))

    # DELETE 原 transactions + holdings
    for txn in txns:
        await session.delete(txn)
    await session.delete(holding)
    await session.flush()

    return closed.id
