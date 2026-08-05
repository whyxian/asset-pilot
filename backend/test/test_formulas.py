"""formulas.py 财务公式单元测试 — 做T ROI / 组合聚合 / XIRR / Modified Dietz

这些公式直接决定前端盈亏展示的正确性，是 2026-08-04 盘点后补的关键缺口。
"""

from datetime import date
from decimal import Decimal

from app.core.formulas import (
    calculate_modified_dietz,
    calculate_portfolio_overview,
    calculate_remaining_position_roi,
    calculate_xirr,
)


# ════════════════════════════════════════════════════
# calculate_remaining_position_roi（做T流持仓收益率）
# ════════════════════════════════════════════════════

def test_roi_normal_cost_positive():
    """正常持仓（成本 > 0）：ROI = (现价 - 成本) / 成本 × 100%"""
    r = calculate_remaining_position_roi(
        current_price=Decimal("12"), broker_cost_price=Decimal("10"),
        initial_buy_price=Decimal("10"), total_shares=Decimal("100"),
    )
    assert r["success"] is True
    assert r["rate_of_return"] == 20.0
    assert r["net_profit"] == Decimal("200")
    assert r["is_crazy_trader"] is False


def test_roi_crazy_trader_zero_cost():
    """做T至 0 成本：ROI = (现价 - 0) / 建仓价 × 100%，标记 is_crazy_trader"""
    r = calculate_remaining_position_roi(
        current_price=Decimal("12"), broker_cost_price=Decimal("0"),
        initial_buy_price=Decimal("10"), total_shares=Decimal("50"),
    )
    assert r["success"] is True
    assert r["rate_of_return"] == 120.0  # 12/10 × 100
    assert r["net_profit"] == Decimal("600")  # (12-0) × 50
    assert r["is_crazy_trader"] is True


def test_roi_crazy_trader_negative_cost():
    """做T至负成本：ROI = (现价 - 负成本) / 建仓价 × 100%"""
    r = calculate_remaining_position_roi(
        current_price=Decimal("15"), broker_cost_price=Decimal("-5"),
        initial_buy_price=Decimal("10"), total_shares=Decimal("20"),
    )
    assert r["success"] is True
    assert r["rate_of_return"] == 200.0  # (15+5)/10 × 100
    assert r["net_profit"] == Decimal("400")  # (15+5) × 20
    assert r["is_crazy_trader"] is True


def test_roi_dirty_initial_buy_price():
    """建仓价 ≤ 0 脏数据：无法算收益率，只返回净利润"""
    r = calculate_remaining_position_roi(
        current_price=Decimal("12"), broker_cost_price=Decimal("-3"),
        initial_buy_price=Decimal("0"), total_shares=Decimal("10"),
    )
    assert r["success"] is True
    assert r["rate_of_return"] is None
    assert r["net_profit"] == Decimal("150")
    assert r["is_crazy_trader"] is False


def test_roi_exception_returns_success_false():
    """计算异常（如非法输入）→ success=False，不抛异常（2026-08-05 修复：转换移入 try）"""
    r = calculate_remaining_position_roi(
        current_price=None, broker_cost_price=Decimal("10"),
        initial_buy_price=Decimal("10"), total_shares=Decimal("100"),
    )
    assert r["success"] is False
    assert r["rate_of_return"] is None
    assert r["net_profit"] is None


# ════════════════════════════════════════════════════
# calculate_portfolio_overview（组合盈亏聚合）
# ════════════════════════════════════════════════════

def test_overview_normal_aggregation():
    """正常组合：多币种市值/成本换算 USD 聚合 + 总成本>0 盈亏率"""
    holdings = [
        {"total_shares": Decimal("100"), "current_price": Decimal("12"),
         "broker_cost_price": Decimal("10"), "initial_buy_price": Decimal("10"),
         "currency": "CNY"},
        {"total_shares": Decimal("10"), "current_price": Decimal("110"),
         "broker_cost_price": Decimal("100"), "initial_buy_price": Decimal("100"),
         "currency": "USD"},
    ]
    rates = {"CNY": Decimal("7.2"), "USD": Decimal("1.0")}
    r = calculate_portfolio_overview(holdings, rates)
    assert r["success"] is True
    # 市值 = 1200/7.2 + 1100 = 166.67 + 1100 = 1266.67
    assert r["total_value"] == Decimal("1266.666666666666666666666667")
    # 成本 = 1000/7.2 + 1000 = 1138.89
    # 盈亏 = 127.78，盈亏率 = 127.78/1138.89 × 100 = 11.22%
    assert r["rate_of_return"] > 11.0 and r["rate_of_return"] < 11.5
    assert r["is_crazy_trader"] is False


def test_overview_crazy_trader_uses_initial_price():
    """总成本 ≤ 0（做T抽干本金）：盈亏率用总首买成本作分母"""
    holdings = [
        {"total_shares": Decimal("100"), "current_price": Decimal("12"),
         "broker_cost_price": Decimal("-2"), "initial_buy_price": Decimal("10"),
         "currency": "CNY"},
    ]
    rates = {"CNY": Decimal("7.2")}
    r = calculate_portfolio_overview(holdings, rates)
    assert r["success"] is True
    assert r["is_crazy_trader"] is True
    # 总成本 = -200/7.2 ≤ 0 → 分母用首买成本 1000/7.2
    # 盈亏 = (1200+200)/7.2 = 194.44；盈亏率 = 194.44/138.89 × 100 = 140%
    assert r["rate_of_return"] > 139.0 and r["rate_of_return"] < 141.0


def test_overview_all_zero_initial_cost():
    """总成本与总首买成本都 ≤ 0 → rate_of_return=None"""
    holdings = [
        {"total_shares": Decimal("100"), "current_price": Decimal("0"),
         "broker_cost_price": Decimal("-2"), "initial_buy_price": Decimal("0"),
         "currency": "CNY"},
    ]
    rates = {"CNY": Decimal("7.2")}
    r = calculate_portfolio_overview(holdings, rates)
    assert r["success"] is True
    assert r["rate_of_return"] is None
    assert r["is_crazy_trader"] is True


def test_overview_missing_rate_falls_back_to_1():
    """汇率缺失 → 兜底 1.0（按原币聚合），不抛异常"""
    holdings = [
        {"total_shares": Decimal("10"), "current_price": Decimal("100"),
         "broker_cost_price": Decimal("90"), "initial_buy_price": Decimal("90"),
         "currency": "EUR"},
    ]
    r = calculate_portfolio_overview(holdings, {"CNY": Decimal("7.2")})
    assert r["success"] is True
    assert r["total_value"] == Decimal("1000")


# ════════════════════════════════════════════════════
# calculate_xirr（区间内部收益率）
# ════════════════════════════════════════════════════

def test_xirr_no_flows_flat():
    """无流水 + 市值不变 → 0%"""
    r = calculate_xirr(Decimal("1000"), Decimal("1000"), [], "2026-01-01", "2026-12-31")
    assert r["success"] is True
    assert abs(r["rate_of_return"]) < 0.01
    assert r["net_profit"] == Decimal("0")


def test_xirr_double_in_one_year():
    """一年翻倍 → 100%"""
    r = calculate_xirr(Decimal("1000"), Decimal("2000"), [], "2026-01-01", "2026-12-31")
    assert r["success"] is True
    assert abs(r["rate_of_return"] - 100.0) < 0.5


def test_xirr_double_in_half_year():
    """半年翻倍（181 天）→ 年化 ≈ 2^(365/181) - 1 ≈ 304.6%"""
    r = calculate_xirr(Decimal("1000"), Decimal("2000"), [], "2026-01-01", "2026-07-01")
    assert r["success"] is True
    assert abs(r["rate_of_return"] - 304.6) < 1.0


def test_xirr_with_midterm_flow():
    """期间买入 5000（现金流出袋）→ 年化复利计入时间价值"""
    # V0=10000 年初，年中投入 5000，年末市值 16500
    # 净利 = 16500 - 10000 - 5000 = 1500
    r = calculate_xirr(
        Decimal("10000"), Decimal("16500"),
        [{"date": "2026-07-01", "amount": Decimal("5000")}],
        "2026-01-01", "2026-12-31",
    )
    assert r["success"] is True
    assert r["net_profit"] == Decimal("1500")
    assert r["rate_of_return"] > 0  # 半年投入 5000 换回 1500 超额，年化 > 0


def test_xirr_no_solution_returns_none():
    """全负现金流（无解）→ 不抛异常，rate=None"""
    # pyxirr 对全负现金流抛 InvalidPaymentsError，被安全阀捕获返回 success=False
    r = calculate_xirr(
        Decimal("1000"), Decimal("-100"),
        [], "2026-01-01", "2026-12-31",
    )
    assert r["success"] is False
    assert r["rate_of_return"] is None


# ════════════════════════════════════════════════════
# calculate_modified_dietz（修正迪茨法）
# ════════════════════════════════════════════════════

def test_dietz_no_flows():
    """无流水：ROI = (V1 - V0) / V0 × 100%"""
    r = calculate_modified_dietz(Decimal("10000"), Decimal("11000"), [], "2026-01-01", "2026-01-31")
    assert r["success"] is True
    assert abs(r["rate_of_return"] - 10.0) < 0.001
    assert r["net_profit"] == Decimal("1000")


def test_dietz_with_flow_weight():
    """期间投入按时间权重折算：第 10 天投入 5000，W = (30-10)/30 = 2/3"""
    r = calculate_modified_dietz(
        Decimal("10000"), Decimal("17000"),
        [{"date": "2026-01-10", "amount": Decimal("5000")}],
        "2026-01-01", "2026-01-31",
    )
    assert r["success"] is True
    # Di = 1/10 - 1/1 = 9 天；Wi = (30-9)/30 = 0.7
    # 分子 = 17000-10000-5000 = 2000；分母 = 10000 + 5000×0.7 = 13500
    # ROI = 2000/13500 × 100 ≈ 14.81%
    assert abs(r["rate_of_return"] - 14.81) < 0.05
    assert r["net_profit"] == Decimal("2000")


def test_dietz_same_day_protects_division():
    """当天买卖（CD=0）→ CD 兜底 1，不除零"""
    r = calculate_modified_dietz(Decimal("1000"), Decimal("1100"), [], "2026-01-01", "2026-01-01")
    assert r["success"] is True
    assert abs(r["rate_of_return"] - 10.0) < 0.001


def test_dietz_zero_denominator_marks_crazy():
    """分母 ≤ 0（期初 0 本金）→ rate=None + is_crazy_trader=True"""
    r = calculate_modified_dietz(
        Decimal("0"), Decimal("100"),
        [{"date": "2026-01-10", "amount": Decimal("-100")}],
        "2026-01-01", "2026-01-31",
    )
    assert r["success"] is True
    assert r["rate_of_return"] is None
    assert r["is_crazy_trader"] is True
    assert r["net_profit"] == Decimal("200")
