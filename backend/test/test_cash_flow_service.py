"""CashFlowService / 现金联动单元测试

覆盖：入金/出金/余额换算 + 建仓/勘误/买卖交易/删持仓 全链路现金联动
（2026-08-04 修复后补：update_holding 勘误联动 + delete_holding 删流水）
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.exceptions import BusinessError
from app.models.asset_holding import AssetHoldingCreate, AssetHoldingUpdate
from app.models.asset_quote import AssetQuote
from app.models.cash_flow import CashDepositCreate, CashWithdrawCreate
from app.models.orm.cash_flow_orm import CashFlowRecord
from app.models.transaction import TransactionCreate
from app.services.asset_holding_service import AssetHoldingService
from app.services.cash_flow_service import CashFlowService
from app.services.transaction_service import TransactionService
from test.conftest import approx


async def _cash_sum(Session) -> Decimal:
    """全部币种现金余额合计"""
    async with Session() as s:
        return Decimal(str((await s.execute(
            select(func.coalesce(func.sum(CashFlowRecord.amount), 0))
        )).scalar()))


async def _cash_count(Session) -> int:
    """流水条数"""
    async with Session() as s:
        return (await s.execute(select(func.count()).select_from(CashFlowRecord))).scalar()


async def _deposit(Session, amount: str, currency: str = "CNY") -> None:
    """直接插入一笔入金流水（模拟外部入金）"""
    async with Session() as s:
        s.add(CashFlowRecord(type="deposit", amount=Decimal(amount), currency=currency))
        await s.commit()


def _mock_holding_quote(svc: AssetHoldingService, monkeypatch) -> None:
    """mock 建仓时的行情拉取（返回 TEST 的行情，触发缓存预热 + 校验可用性）"""
    async def fake_fetch(ac, market, tickers, force_refresh=False):
        return [AssetQuote(
            ticker="TEST", asset_class="STOCK", market="CN",
            name="测试品种", price=Decimal("12"), currency="CNY", source="TEST",
        )]
    monkeypatch.setattr(svc._quote_svc, "fetch_quotes_by_asset_class", fake_fetch)


# ════════════════════════════════════════════════════
# 入金 / 出金 / 余额换算
# ════════════════════════════════════════════════════

async def test_deposit_withdraw_and_balance_conversion(Session, monkeypatch):
    """入金正流水、出金负流水；get_balances 按显示币种换算总额（mock 汇率）"""
    from app.utils.exchange_rate import RatesSnapshot

    async def fake_fetch_rates():
        # USD-base rates：1 USD = 7.2 CNY
        return RatesSnapshot(rates={"USD": 1.0, "CNY": 7.2}, source_date="2026-08-04", is_stale=False)
    monkeypatch.setattr("app.services.cash_flow_service.fetch_rates", fake_fetch_rates)

    svc = CashFlowService()
    await svc.deposit(CashDepositCreate(amount=Decimal("1000"), currency="CNY"))
    await svc.withdraw(CashWithdrawCreate(amount=Decimal("300"), currency="CNY"))
    # USD 入金 100 → 按 7.2 换算
    await svc.deposit(CashDepositCreate(amount=Decimal("100"), currency="USD"))

    assert await _cash_count(Session) == 3
    assert approx(await _cash_sum(Session), "800")  # 1000 - 300 + 100（原币直加）

    balances = await svc.get_balances(display_currency="CNY")
    assert approx(balances.total, "1420")  # 700 + 100 × 7.2
    assert balances.display_currency == "CNY"
    assert balances.rate_stale is False


# ════════════════════════════════════════════════════
# 建仓联动
# ════════════════════════════════════════════════════

async def test_create_holding_no_cash_generates_deposit_and_buy(Session, seed_variety, monkeypatch):
    """建仓不勾选现金账户 → 自动入金等额（历史本金）+ buy 扣款，两条流水"""
    await seed_variety(ticker="TEST", asset_class="STOCK", market="CN", currency="CNY")
    svc = AssetHoldingService()
    _mock_holding_quote(svc, monkeypatch)

    await svc.create_holding(AssetHoldingCreate(
        ticker="TEST", name="测试", asset_class="STOCK", market="CN",
        currency="CNY", quantity=Decimal("100"), cost_price=Decimal("10"),
        total_invested=Decimal("1000"), first_buy_date="2026-08-01",
        cash_account_enabled=False,
    ))
    assert await _cash_count(Session) == 2
    assert await _cash_sum(Session) == Decimal("0")  # 入金 1000 + 扣款 -1000


async def test_create_holding_cash_enabled_deducts_balance(Session, seed_variety, monkeypatch):
    """建仓勾选现金账户 → 从余额扣款，无自动入金"""
    await seed_variety(ticker="TEST", asset_class="STOCK", market="CN", currency="CNY")
    svc = AssetHoldingService()
    _mock_holding_quote(svc, monkeypatch)
    await _deposit(Session, "2000")

    await svc.create_holding(AssetHoldingCreate(
        ticker="TEST", name="测试", asset_class="STOCK", market="CN",
        currency="CNY", quantity=Decimal("100"), cost_price=Decimal("10"),
        total_invested=Decimal("1000"), first_buy_date="2026-08-01",
        cash_account_enabled=True,
    ))
    assert await _cash_count(Session) == 2  # 手动入金 + buy 扣款
    assert approx(await _cash_sum(Session), "1000")


async def test_create_holding_cash_enabled_insufficient_rejected(Session, seed_variety, monkeypatch):
    """建仓勾选现金账户但余额不足 → 拒绝"""
    await seed_variety(ticker="TEST", asset_class="STOCK", market="CN", currency="CNY")
    svc = AssetHoldingService()
    _mock_holding_quote(svc, monkeypatch)

    with pytest.raises(BusinessError, match="现金余额不足"):
        await svc.create_holding(AssetHoldingCreate(
            ticker="TEST", name="测试", asset_class="STOCK", market="CN",
            currency="CNY", quantity=Decimal("100"), cost_price=Decimal("10"),
            total_invested=Decimal("1000"), first_buy_date="2026-08-01",
            cash_account_enabled=True,
        ))
    assert await _cash_count(Session) == 0  # 事务回滚，无残留


# ════════════════════════════════════════════════════
# 编辑持仓（勘误交易）联动
# ════════════════════════════════════════════════════

async def test_update_holding_qty_increase_generates_buy_flow(Session, seed_holding, monkeypatch):
    """改份额 +50 → buy 勘误交易联动扣款流水（校验余额）"""
    await seed_holding(qty="100", cost="10", total="1000")
    svc = AssetHoldingService()
    await _deposit(Session, "2000")

    await svc.update_holding("TEST", "STOCK", "CN", AssetHoldingUpdate(quantity=Decimal("150")))
    # seed 本金 1000 + 入金 2000 - 500（+50 股 @10）= 2500
    assert approx(await _cash_sum(Session), "2500")
    assert await _cash_count(Session) == 3  # seed 本金 + 入金 + 勘误 buy 扣款


async def test_update_holding_qty_decrease_generates_sell_flow(Session, seed_holding):
    """改份额 -50 → sell 勘误交易联动入账流水"""
    await seed_holding(qty="100", cost="10", total="1000")
    svc = AssetHoldingService()

    await svc.update_holding("TEST", "STOCK", "CN", AssetHoldingUpdate(quantity=Decimal("50")))
    # seed 本金 1000 + 500（-50 股 @10 入账）= 1500
    assert approx(await _cash_sum(Session), "1500")
    assert await _cash_count(Session) == 2


async def test_update_holding_insufficient_rejected(Session, seed_holding):
    """余额不足时加仓勘误 → 拒绝且事务回滚"""
    await seed_holding(qty="100", cost="10", total="1000")
    svc = AssetHoldingService()
    await _deposit(Session, "400")  # seed 本金 1000 + 400 = 1400

    with pytest.raises(BusinessError, match="现金余额不足"):
        # 改到 300 股需补 200 × 10 = 2000 > 1400
        await svc.update_holding("TEST", "STOCK", "CN", AssetHoldingUpdate(quantity=Decimal("300")))
    assert await _cash_count(Session) == 2  # 回滚后只剩 seed 本金 + 手动入金


# ════════════════════════════════════════════════════
# 删除持仓联动
# ════════════════════════════════════════════════════

async def test_delete_holding_removes_linked_flows(Session, seed_variety, monkeypatch):
    """删持仓 → 关联 buy/sell 流水删除；自动入金（transaction_id=NULL）保留"""
    await seed_variety(ticker="TEST", asset_class="STOCK", market="CN", currency="CNY")
    svc = AssetHoldingService()
    _mock_holding_quote(svc, monkeypatch)

    # 建仓（自动入金 1000 + 扣款 -1000）+ 手动入金 2000
    await svc.create_holding(AssetHoldingCreate(
        ticker="TEST", name="测试", asset_class="STOCK", market="CN",
        currency="CNY", quantity=Decimal("100"), cost_price=Decimal("10"),
        total_invested=Decimal("1000"), first_buy_date="2026-08-01",
        cash_account_enabled=False,
    ))
    await _deposit(Session, "2000")
    assert await _cash_count(Session) == 3

    deleted = await svc.delete_holding("TEST", "STOCK", "CN")
    assert deleted == 1  # 建仓 buy 交易
    assert await _cash_count(Session) == 2  # 自动入金 + 手动入金
    assert approx(await _cash_sum(Session), "3000")


# ════════════════════════════════════════════════════
# 交易页买卖联动
# ════════════════════════════════════════════════════

async def test_transaction_buy_auto_flow_and_delete_rollback(Session, seed_holding):
    """交易页新增 buy（只填数量+单价）→ 联动按 qty×price 生成扣款流水；删除交易 → 流水回退"""
    await seed_holding(qty="100", cost="10", total="1000")
    await _deposit(Session, "2000")
    svc = TransactionService()

    txn = await svc.create_transaction(TransactionCreate(
        ticker="TEST", asset_class="STOCK", market="CN",
        transaction_date=date(2024, 6, 1), type="buy",
        quantity=Decimal("30"), unit_price=Decimal("10"),
    ))
    # seed 本金 1000 + 入金 2000 - 300（30 股 @10）= 2700
    assert approx(await _cash_sum(Session), "2700")
    assert await _cash_count(Session) == 3

    await svc.delete_transaction(txn.id)
    assert approx(await _cash_sum(Session), "3000")  # 回退
    assert await _cash_count(Session) == 2


async def test_transaction_sell_auto_flow(Session, seed_holding):
    """交易页新增 sell → 自动入账流水（持仓剩 50 不归档）"""
    await seed_holding(qty="100", cost="10", total="1000")
    await _deposit(Session, "500")
    svc = TransactionService()

    txn = await svc.create_transaction(TransactionCreate(
        ticker="TEST", asset_class="STOCK", market="CN",
        transaction_date=date(2024, 6, 1), type="sell",
        quantity=Decimal("50"), unit_price=Decimal("10"),
    ))
    assert txn is not None
    # seed 本金 1000 + 入金 500 + 500（卖 50 股入账）= 2000
    assert approx(await _cash_sum(Session), "2000")
    assert await _cash_count(Session) == 3
