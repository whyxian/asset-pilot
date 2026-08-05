"""ClosedHoldingService 单元测试 — 归档持仓列表/详情/删除（含删除连带删 cash_flows）

2026-08-04 修复后补：delete_closed_holding 经 closed_transactions.original_id
回溯删除关联 buy/sell 流水，自动入金（transaction_id=NULL）保留。
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.models.orm.cash_flow_orm import CashFlowRecord
from app.models.orm.closed_holding_orm import ClosedHoldingRecord, ClosedTransactionRecord
from app.services.closed_holding_service import ClosedHoldingService


async def _seed_closed_holding(Session, ticker: str = "TEST") -> int:
    """构造一条归档持仓 + 2 条归档交易（original_id 指向已删除的原交易）+ 关联流水"""
    async with Session() as s:
        h = ClosedHoldingRecord(
            ticker=ticker, name=ticker, market="CN", asset_class="STOCK", currency="CNY",
            total_buy_amount=Decimal("1000"), first_buy_date=date(2024, 1, 1),
            first_buy_price=Decimal("10"), closed_at=date(2024, 6, 1),
            holding_days=152, realized_pnl=Decimal("200"), pnl_pct=Decimal("20"),
            is_crazy_trader=False,
        )
        s.add(h)
        await s.flush()
        # 原交易 id = 1, 2（已被删除，original_id 追溯）
        t1 = ClosedTransactionRecord(
            closed_holding_id=h.id, ticker=ticker, asset_class="STOCK", market="CN",
            transaction_date=date(2024, 1, 1), type="buy",
            quantity=Decimal("100"), unit_price=Decimal("10"),
            amount=Decimal("1000"), notes="建仓", original_id=1,
        )
        t2 = ClosedTransactionRecord(
            closed_holding_id=h.id, ticker=ticker, asset_class="STOCK", market="CN",
            transaction_date=date(2024, 6, 1), type="sell",
            quantity=Decimal("100"), unit_price=Decimal("12"),
            amount=Decimal("1200"), notes="清仓", original_id=2,
        )
        s.add_all([t1, t2])
        # 关联流水：buy 扣款 -1000（txn=1）、sell 入账 +1200（txn=2）、自动入金 +1000（txn=NULL）
        s.add_all([
            CashFlowRecord(type="buy", amount=Decimal("-1000"), currency="CNY", transaction_id=1),
            CashFlowRecord(type="sell", amount=Decimal("1200"), currency="CNY", transaction_id=2),
            CashFlowRecord(type="deposit", amount=Decimal("1000"), currency="CNY", transaction_id=None),
        ])
        await s.commit()
        return h.id


async def _cash_count(Session) -> int:
    async with Session() as s:
        return (await s.execute(select(func.count()).select_from(CashFlowRecord))).scalar()


async def test_list_closed_holdings_paginated(Session):
    """归档持仓列表：倒序 + 分页 + total"""
    await _seed_closed_holding(Session, "AAA")
    await _seed_closed_holding(Session, "BBB")

    svc = ClosedHoldingService()
    page1 = await svc.list_closed_holdings(page=1, page_size=1)
    assert page1.total == 2
    assert len(page1.data) == 1
    assert page1.data[0].ticker == "BBB"  # 后插入的排前面（同 closed_at 按 id 倒序）

    page2 = await svc.list_closed_holdings(page=2, page_size=1)
    assert page2.data[0].ticker == "AAA"


async def test_get_closed_holding_detail_with_transactions(Session):
    """详情：含全部归档交易（按交易日升序）"""
    hid = await _seed_closed_holding(Session)

    detail = await ClosedHoldingService().get_closed_holding(hid)
    assert detail is not None
    assert detail.ticker == "TEST"
    assert detail.realized_pnl == Decimal("200")
    assert len(detail.transactions) == 2
    assert [t.type for t in detail.transactions] == ["buy", "sell"]
    assert detail.transactions[0].original_id == 1


async def test_get_closed_holding_missing_returns_none(Session):
    assert await ClosedHoldingService().get_closed_holding(999) is None


async def test_delete_closed_holding_removes_linked_flows(Session):
    """删除归档持仓：关联 buy/sell 流水删除，自动入金（txn_id=NULL）保留"""
    hid = await _seed_closed_holding(Session)
    assert await _cash_count(Session) == 3

    assert await ClosedHoldingService().delete_closed_holding(hid) is True

    # 归档持仓 + 归档交易 + 关联流水都删掉
    async with Session() as s:
        assert (await s.execute(select(ClosedHoldingRecord))).scalars().all() == []
        assert (await s.execute(select(ClosedTransactionRecord))).scalars().all() == []
    assert await _cash_count(Session) == 1  # 只剩自动入金

    # 删除后详情与列表为空
    assert await ClosedHoldingService().get_closed_holding(hid) is None
    assert (await ClosedHoldingService().list_closed_holdings()).total == 0


async def test_delete_missing_returns_false(Session):
    assert await ClosedHoldingService().delete_closed_holding(999) is False
