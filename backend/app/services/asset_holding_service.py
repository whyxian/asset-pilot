"""持仓业务逻辑

数据约束：(asset_class, market, ticker) 三元组唯一定位一笔持仓。
所有按品种操作的函数都必须传完整三元组。
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.asset_holding import AssetHolding, AssetHoldingCreate, AssetHoldingUpdate, HoldingWithQuote
from app.models.orm.transaction_orm import TransactionRecord
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

    async def get_holding(
        self, ticker: str, asset_class: str, market: str
    ) -> AssetHolding | None:
        """按三元组获取持仓"""
        return await self._repo.get_holding(ticker, asset_class, market)

    async def create_holding(self, data: AssetHoldingCreate) -> AssetHolding:
        """新增持仓（建仓 = 设定基线，校验品种是否存在，名称空时从品种记录自动补填）"""
        variety = await self._variety_repo.get_variety(data.ticker, data.asset_class, data.market)
        if not variety:
            raise BusinessError(40001, f"未识别的品种代码 '{data.ticker}'，请先通过 /api/v1/varieties 添加该品种")
        # 前端可能未传 name，从品种记录补填
        if not data.name:
            data = data.model_copy(update={"name": variety.name})
        return await self._repo.create_holding(data)

    async def update_holding(
        self, ticker: str, asset_class: str, market: str, data: AssetHoldingUpdate
    ) -> AssetHolding | None:
        """更新持仓 — 修改 baseline 后触发该 ticker 的全量重算

        注意：用户在持仓页修改 quantity/cost_price/total_invested 时，
        repository 已将其同步到 initial_*。此处需调用重算，使派生字段
        反映"新基线 + 现有交易回放"的结果。如该 ticker 没有交易，
        重算结果 == 新 baseline，等价于直接修改派生字段。
        """
        result = await self._repo.update_holding(ticker, asset_class, market, data)
        if result is None:
            return None

        # 仅在 baseline 字段被修改时触发重算
        update_dict = data.model_dump(exclude_unset=True)
        if any(k in update_dict for k in ("quantity", "cost_price", "total_invested")):
            from app.core.database import async_session  # 局部导入避免循环
            async with async_session() as session:
                await recompute_holding(session, ticker, asset_class, market)
                await session.commit()
            # 重算后再读一次返回最新值
            return await self._repo.get_holding(ticker, asset_class, market)
        return result

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

    async def list_holdings_with_quotes(self) -> list[HoldingWithQuote]:
        """获取持仓列表，合并实时行情并计算市值/盈亏/年化

        Returns:
            带实时行情的持仓列表
        """
        holdings = await self._repo.list_holdings()
        if not holdings:
            return []

        # 按 (asset_class, market) 分组，批量获取行情（已清仓品种 quantity=0 也参与，便于前端展示历史价格）
        groups = defaultdict(list)
        for h in holdings:
            groups[(h.asset_class, h.market)].append(h.ticker)

        quote_map = {}
        for (ac, market), tickers in groups.items():
            quotes = await self._quote_svc.fetch_quotes_by_asset_class(ac, market, tickers)
            for q in quotes:
                # 行情按 (asset_class, market, ticker) 三元组定位，避免不同品种 ticker 冲突
                quote_map[(ac, market, q.ticker)] = q

        today = date.today()
        results = []
        for h in holdings:
            q = quote_map.get((h.asset_class, h.market, h.ticker))
            current_price = q.price if q else Decimal("0")
            market_value = h.quantity * current_price
            pnl = market_value - h.total_invested

            # 盈亏百分比
            pnl_pct: float | str | None = None
            if h.total_invested > 0:
                pnl_pct = float((pnl / h.total_invested) * 100)
            elif h.total_invested == 0 and market_value > 0:
                pnl_pct = "+∞%"  # 零成本持有，盈亏率无穷大

            # 简单年化回报率 = 总收益率 × (365 / 持有天数)
            # 持有天数 = (今日 - 首次买入日) + 1，当天买入也算持有 1 天
            annualized: float | str | None = None
            if h.cost_price > 0 and h.first_buy_date:
                holding_days = (today - h.first_buy_date).days + 1
                if holding_days >= 1:
                    total_return_pct = float((current_price - h.cost_price) / h.cost_price) * 100
                    annualized = round(total_return_pct * (365 / holding_days), 4)
            elif h.cost_price == 0 and current_price > 0 and h.first_buy_date:
                annualized = "+∞%"  # 零成本持有，年化无穷大

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
                liquidated_at=h.liquidated_at,
                current_price=current_price,
                market_value=market_value,
                pnl=pnl,
                pnl_pct=pnl_pct,
                annualized_return=annualized,
            ))

        return results


async def recompute_holding(
    session: AsyncSession, ticker: str, asset_class: str, market: str
) -> None:
    """全量重算指定品种的派生持仓字段（quantity / cost_price / total_invested / liquidated_at）

    算法：
        1. 以 holdings 行的 initial_* 三列作为起点 (q, p, t)
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

    # 起点 = 建仓基线
    q = Decimal(str(holding.initial_quantity))
    p = Decimal(str(holding.initial_cost_price))
    t = Decimal(str(holding.initial_total_invested))

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
            # 下限 0："白拿股票"上限 — 做 T 累计赚到比总投入还多时不允许成本为负
            if t < 0:
                t = Decimal("0")

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

    # 计算 realized_pnl：sum(sell.amount) - sum(buy.amount) - initial_total_invested
    # 含义：交易期间的净现金流 - 建仓时假设已投入的初始资金 = 该周期净盈亏
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

    initial_t = Decimal(str(holding.initial_total_invested))
    realized_pnl = sum_sell - sum_buy - initial_t

    # 清仓日期：取 holdings 当前 liquidated_at（recompute 刚写好）；兜底用最后一笔 sell 日期
    closed_at = holding.liquidated_at
    if closed_at is None:
        last_sell = next((x for x in reversed(txns) if x.type == "sell"), None)
        if last_sell is None:
            # 极端：quantity=0 但没有 sell（建仓基线 q=0？）— 拒绝归档
            raise BusinessError(40001, f"持仓 '{ticker}' 没有清仓日期，无法归档")
        closed_at = last_sell.transaction_date

    holding_days = (closed_at - holding.first_buy_date).days + 1

    # INSERT closed_holdings
    closed = ClosedHoldingRecord(
        ticker=holding.ticker,
        name=holding.name,
        market=holding.market,
        asset_class=holding.asset_class,
        currency=holding.currency,
        initial_quantity=holding.initial_quantity,
        initial_cost_price=holding.initial_cost_price,
        initial_total_invested=holding.initial_total_invested,
        first_buy_date=holding.first_buy_date,
        closed_at=closed_at,
        holding_days=holding_days,
        realized_pnl=realized_pnl,
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
            notes=txn.notes,
            original_id=txn.id,
        ))

    # DELETE 原 transactions + holdings
    for txn in txns:
        await session.delete(txn)
    await session.delete(holding)
    await session.flush()

    return closed.id
