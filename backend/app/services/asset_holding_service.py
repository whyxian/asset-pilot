"""持仓业务逻辑"""

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

    async def get_holding(self, ticker: str) -> AssetHolding | None:
        """按代码获取持仓"""
        return await self._repo.get_holding(ticker)

    async def create_holding(self, data: AssetHoldingCreate) -> AssetHolding:
        """新增持仓（建仓 = 设定基线，校验品种是否存在，名称空时从品种记录自动补填）"""
        variety = await self._variety_repo.get_variety(data.ticker, data.asset_class, data.market)
        if not variety:
            raise BusinessError(40001, f"未识别的品种代码 '{data.ticker}'，请先通过 /api/v1/varieties 添加该品种")
        # 前端可能未传 name，从品种记录补填
        if not data.name:
            data = data.model_copy(update={"name": variety.name})
        return await self._repo.create_holding(data)

    async def update_holding(self, ticker: str, data: AssetHoldingUpdate) -> AssetHolding | None:
        """更新持仓 — 修改 baseline 后触发该 ticker 的全量重算

        注意：用户在持仓页修改 quantity/cost_price/total_invested 时，
        repository 已将其同步到 initial_*。此处需调用重算，使派生字段
        反映"新基线 + 现有交易回放"的结果。如该 ticker 没有交易，
        重算结果 == 新 baseline，等价于直接修改派生字段。
        """
        result = await self._repo.update_holding(ticker, data)
        if result is None:
            return None

        # 仅在 baseline 字段被修改时触发重算
        update_dict = data.model_dump(exclude_unset=True)
        if any(k in update_dict for k in ("quantity", "cost_price", "total_invested")):
            from app.core.database import async_session  # 局部导入避免循环
            async with async_session() as session:
                await recompute_holding(session, ticker)
                await session.commit()
            # 重算后再读一次返回最新值
            return await self._repo.get_holding(ticker)
        return result

    async def delete_holding(self, ticker: str) -> bool:
        """删除持仓 — 拒绝删除有关联交易记录的持仓，防止孤儿数据"""
        from app.core.database import async_session
        async with async_session() as session:
            txn_count = (await session.execute(
                select(TransactionRecord).where(TransactionRecord.ticker == ticker).limit(1)
            )).scalar_one_or_none()
            if txn_count is not None:
                raise BusinessError(
                    40001,
                    f"持仓 '{ticker}' 仍有关联的交易记录，请先在交易页删除全部相关交易后再删除持仓",
                )
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
            quotes = await self._quote_svc.fetch_quotes_by_asset_class(ac, market, tickers)
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


async def recompute_holding(session: AsyncSession, ticker: str) -> None:
    """全量重算指定 ticker 的派生持仓字段（quantity / cost_price / total_invested）

    算法：
        1. 以 holdings 行的 initial_* 三列作为起点 (q, p, t)
        2. 按 (transaction_date 升序, id 升序) 顺序回放该 ticker 全部交易：
           - buy:  amt = transaction.amount 优先，否则 quantity * unit_price
                   new_q = q + qty
                   new_t = t + amt
                   new_p = new_t / new_q
           - sell: 加权平均法 — cost_price 不变，total_invested 按比例减
                   if qty > q: 抛出 BusinessError "卖超"
                   new_q = q - qty
                   new_t = t - p * qty
                   new_p = p (清仓时归零)
        3. 写回 holdings 的派生字段；first_buy_date 不动

    Args:
        session: 外部传入的 session（必须由调用方控制 commit/rollback）
        ticker: 持仓代码

    Raises:
        BusinessError: holdings 中不存在该 ticker，或某笔 sell 卖超
    """
    from app.repositories.asset_holding_repository import AssetHoldingRepository
    repo = AssetHoldingRepository()

    # 取持仓 ORM 记录
    holding = await repo.get_record_in_session(session, ticker)
    if holding is None:
        raise BusinessError(40401, f"持仓 '{ticker}' 不存在，无法重算")

    # 起点 = 建仓基线
    q = Decimal(str(holding.initial_quantity))
    p = Decimal(str(holding.initial_cost_price))
    t = Decimal(str(holding.initial_total_invested))

    # 按时间正序回放该 ticker 的全部交易
    txns = (await session.execute(
        select(TransactionRecord)
        .where(TransactionRecord.ticker == ticker)
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
            # 加权平均法：成本价不变，总投入按比例减
            t = t - p * qty
            q = q - qty
            if q == 0:
                p = Decimal("0")
                t = Decimal("0")  # 清仓后总投入归零
        else:
            raise BusinessError(40001, f"未知交易类型 '{txn.type}'（交易 #{txn.id}）")

    # 写回派生字段
    holding.quantity = q
    holding.cost_price = p
    holding.total_invested = t
    # session.commit() 由调用方负责

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
            quotes = await self._quote_svc.fetch_quotes_by_asset_class(ac, market, tickers)
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
