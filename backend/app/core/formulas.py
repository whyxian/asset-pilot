from datetime import datetime
from decimal import Decimal

from pyxirr import xirr


def calculate_remaining_position_roi(current_price, broker_cost_price, initial_buy_price, total_shares):
    """
    方法名称：做T流个股持仓收益率（Remaining Position ROI for Grid Traders）

    数学公式：
        1. 当 成本价 > 0 时（正常持仓）：
           ROI = (当前股价 - 券商成本价) / 券商成本价 * 100%
        2. 当 成本价 <= 0 时（做T至负成本/0成本）：
           ROI = (当前股价 - 券商成本价) / 当初建仓时的实际股价 * 100%

    适用场景：
        用于【个股持仓看板】列表。完美解决高抛低吸选手把持仓成本做到 0 或负数时，
        券商 App 收益率公式直接崩溃（显示 NaN、无穷大或异常负数）的痛点。

    参数说明：
        current_price (Decimal): 当前股票最新的公允市场价格。
        broker_cost_price (Decimal): 券商后台显示的持仓成本价（做T狂魔该值通常 <= 0）。
        initial_buy_price (Decimal): 该股票最早建仓时的实际第一笔买入价（用作负成本时的理性分母）。
        total_shares (Decimal): 当前账户剩余的持仓股数。

    返回：
        - rate_of_return: float（百分比精度足够）
        - net_profit: Decimal（金额精度，与 PnL 一致）
    """
    D = Decimal
    numerator = None  # 参数转换失败时无净利润可算

    try:
        cp = D(str(current_price))
        bcp = D(str(broker_cost_price))
        ibp = D(str(initial_buy_price))
        ts = D(str(total_shares))

        # 纯账面底仓净利润 = (当前股价 - 券商成本价) * 持仓股数
        numerator = (cp - bcp) * ts
        # 1. 成本大于 0：用正常券商公式计算
        if bcp > 0:
            roi = ((cp - bcp) / bcp) * 100
            is_crazy = False

        # 2. 成本小于等于 0：触发做T流专属"剩余底仓收益率"公式
        else:
            # 初始建仓价异常（应 > 0，=0 为脏数据），无法计算剩余底仓收益率
            if ibp <= 0:
                return {
                    "success": True,
                    "rate_of_return": None,
                    "net_profit": numerator,
                    "is_crazy_trader": False,
                }

            roi = ((cp - bcp) / ibp) * 100
            is_crazy = True

        return {
            "success": True,
            "rate_of_return": round(float(roi), 2),
            "net_profit": numerator,
            "is_crazy_trader": is_crazy,
        }

    except Exception as e:
        # 计算异常（如除零、类型错误等边界情况）
        return {
            "success": False,
            "rate_of_return": None,
            "net_profit": numerator,
            "is_crazy_trader": False,
        }


def calculate_portfolio_overview(holdings, rates):
    """组合概览聚合公式

    方法名称：组合盈亏与盈亏率（Portfolio PnL Aggregation）

    数学公式：
        单只市值 = 持仓股数 × 当前股价
        单只成本 = 持仓股数 × 券商成本价
        单只首买成本 = 持仓股数 × 建仓首笔买入价
        单只市值(USD) = 单只市值 / 汇率[currency]
        单只成本(USD) = 单只成本 / 汇率[currency]
        单只首买成本(USD) = 单只首买成本 / 汇率[currency]
        总市值(USD) = Σ 单只市值(USD)
        总成本(USD) = Σ 单只成本(USD)
        总首买成本(USD) = Σ 单只首买成本(USD)
        总盈亏 = 总市值 - 总成本
        1. 总成本 > 0：总盈亏率 = 总盈亏 / 总成本 × 100%
        2. 总成本 ≤ 0：总盈亏率 = 总盈亏 / 总首买成本 × 100%（剩余底仓收益率，与单只公式一致）

    适用场景：
        概览页 / 快照汇总的组合级盈亏聚合。
        内部完成全部数学运算（市值计算、汇率换算、累加、盈亏率），调用方只传原始数据。

    参数说明：
        holdings (list[dict]): 逐只持仓原始数据，每项含：
            - current_price (Decimal): 当前股票最新的公允市场价格。
            - broker_cost_price (Decimal): 券商后台显示的持仓成本价（做T狂魔该值通常 <= 0）。
            - initial_buy_price (Decimal): 该股票最早建仓时的实际第一笔买入价。
            - total_shares (Decimal): 当前账户剩余的持仓股数。
            - currency (str): 计价货币，如 "CNY" / "USD"
        rates (dict): USD-base 汇率，如 {"CNY": Decimal(7.2), "USD": Decimal(1.0)}

    返回：
        统一返回格式（Decimal 精度）：
        - success: 函数正常执行后恒为 True；异常中断时为 False
        - rate_of_return: 总盈亏率（Decimal），总首买成本也≤0 时为 None
        - net_profit: 总盈亏金额 USD（Decimal）
        - is_crazy_trader: 总成本≤0 时为 True（零成本/负成本持有）
        - total_value: 总市值 USD（Decimal）
        - total_cost: 总成本 USD（Decimal）
    """
    D = Decimal
    total_value = D("0")
    total_cost = D("0")
    total_initial_cost = D("0")

    for h in holdings:
        shares = D(str(h["total_shares"]))
        rate = D(str(rates.get(h["currency"], 1.0)))
        total_value += (shares * D(str(h["current_price"]))) / rate
        total_cost += (shares * D(str(h["broker_cost_price"]))) / rate
        total_initial_cost += (shares * D(str(h["initial_buy_price"]))) / rate

    pnl = total_value - total_cost

    if total_cost > 0:
        return {
            "success": True,
            "rate_of_return": float((pnl / total_cost) * 100),
            "net_profit": pnl,
            "is_crazy_trader": False,
            "total_value": total_value,
            "total_cost": total_cost,
        }
    elif total_initial_cost > 0:
        return {
            "success": True,
            "rate_of_return": float((pnl / total_initial_cost) * 100),
            "net_profit": pnl,
            "is_crazy_trader": True,
            "total_value": total_value,
            "total_cost": total_cost,
        }
    else:
        return {
            "success": True,
            "rate_of_return": None,
            "net_profit": pnl,
            "is_crazy_trader": True,
            "total_value": total_value,
            "total_cost": total_cost,
        }


def calculate_xirr(V0, V1, trade_flows, start_date, end_date):
    """
    方法名称：区间内部收益率（XIRR - Extracted Internal Rate of Return）

    数学公式：
        求解方程使净现值 NPV = 0：
        0 = -V0 + Σ [ -CF_i / (1 + r)^((d_i - d_0)/365) ] + V1 / (1 + r)^((d_end - d_0)/365)
        解出来的 r 即为 XIRR 年化复利收益率。

    适用场景：
        用于【中长周期大盘看板】（建议统计区间 >= 30天）。
        将整个账户视作动态资产池，把买卖看作现金的流入流出，最精准地衡量资金的【时间价值】。
        适合用来与公募基金、标普500等标准年化业绩做跨时空横向对比。

    参数说明：
        V0 (Decimal): 统计起点日期当天的持仓总市值。
        V1 (Decimal): 统计终点日期当天的持仓总市值。
        trade_flows (list): 期间流水列表，格式如 [{'date': '2026-06-01', 'amount': Decimal(5000)}, ...]
                            其中 amount 遵循标准财务视点：买入股票/转入资金为正，卖出/提现为负。
                            amount 已换算为同一币种（USD）。
        start_date (str): 统计起点日期，格式 'YYYY-MM-DD'。
        end_date (str): 统计终点日期，格式 'YYYY-MM-DD'。

    返回：
        rate_of_return: float（pyxirr 计算结果，精度足够）
        net_profit: Decimal（与 PnL 一致的精度）
    """
    D = Decimal

    # 预先计算分子（纯利润）——Decimal 运算，精度与 PnL 一致
    total_cf_for_numerator = sum(D(str(flow['amount'])) for flow in trade_flows)
    numerator = D(str(V1)) - D(str(V0)) - total_cf_for_numerator

    dates = []
    amounts = []  # pyxirr 要求 float

    # XIRR 现金流转换视点：看口袋现金的流向
    # 1. 压入期初快照 (资金离开口袋投入系统，记为负数)
    dates.append(datetime.strptime(start_date, "%Y-%m-%d"))
    amounts.append(-float(D(str(V0))))

    # 2. 压入期间流水 (买入追加 = 现金流出袋记负；卖出提现 = 现金回流口袋记正)
    for flow in trade_flows:
        flow_date = datetime.strptime(flow['date'], "%Y-%m-%d")
        dates.append(flow_date)
        amounts.append(-float(D(str(flow['amount']))))

    # 3. 压入期末快照 (视作最后一天全部空仓清算，资金悉数回口袋，记为正数)
    dates.append(datetime.strptime(end_date, "%Y-%m-%d"))
    amounts.append(float(D(str(V1))))

    try:
        result_r = xirr(dates, amounts)

        # 安全阀：如果 XIRR 无法收敛（通常因为疯狂做T导致本金在初期被彻底抽干，方程出现多重解或无解）
        if result_r is None:
            return {
                "success": True,
                "rate_of_return": None,
                "net_profit": numerator,
                "is_crazy_trader": True,
            }

        roi = result_r * 100
        return {
            "success": True,
            "rate_of_return": round(roi, 2),
            "net_profit": numerator,
            "is_crazy_trader": False,
        }

    except Exception as e:
        # 捕获其他数学边界崩溃（如周期过短、分母尝试除以0、或者无正向现金流）
        return {
            "success": False,
            "rate_of_return": None,
            "net_profit": numerator,
            "is_crazy_trader": False,
        }
    

def calculate_modified_dietz(V0, V1, trade_flows, start_date, end_date):
    """
    方法名称：标准（修正）迪茨法收益率（Modified Dietz Method）

    数学公式：
        ROI = (V1 - V0 - Σ CF_i) / (V0 + Σ (CF_i * W_i)) * 100%
        其中时间权重 W_i = (总自然天数 CD - 该笔流水已过去天数 D_i) / 总自然天数 CD

    适用场景：
        用于【任意时间段切片看板】（如：看上周二到这周四、或者近3天的综合表现）。
        一种国际公认的金额加权回报率算法。它不关心复利，而是通过时间权重将中途进出的钱
        合理折算到"期初总成本"中，能够极其客观地反映某一独立封闭时间区间内的【绝对资产膨胀效率】。

    参数说明：
        V0 (Decimal): 统计起点日期当天的持仓总市值。
        V1 (Decimal): 统计终点日期当天的持仓总市值。
        trade_flows (list): 期间流水列表，格式如 [{'date': '2026-06-01', 'amount': Decimal(5000)}, ...]
                            其中 amount 遵循系统原始流水视点：买入/充钱为正，卖出/提现为负。
                            amount 已换算为同一币种（USD）。
        start_date (str): 统计起点日期，格式 'YYYY-MM-DD'。
        end_date (str): 统计终点日期，格式 'YYYY-MM-DD'。

    返回：
        rate_of_return: 全程 Decimal 运算，最终转 float（% 精度足够）
        net_profit: Decimal（与 PnL 一致的精度，不做 float 转换）
    """
    D = Decimal  # 缩写，内部全程 Decimal

    # 1. 计算总自然天数 (CD)
    CD = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days
    if CD == 0:
        CD = 1  # 防止当天买卖、当天查询导致除以 0

    total_cf = D("0")       # 纯现金流总和 (分子用)
    weighted_cf = D("0")    # 时间加权现金流总和 (分母用)

    # 2. 遍历期间的每一笔流水，计算时间权重（全程 Decimal）
    for flow in trade_flows:
        flow_date = datetime.strptime(flow['date'], "%Y-%m-%d")
        flow_amount = D(str(flow['amount']))

        Di = (flow_date - datetime.strptime(start_date, "%Y-%m-%d")).days
        Wi = D(CD - Di) / D(CD)

        total_cf += flow_amount
        weighted_cf += flow_amount * Wi

    # 3. 计算分子（剔除资金进出水分后的纯投资利润）
    numerator = D(str(V1)) - D(str(V0)) - total_cf

    # 4. 计算分母（期初本金 + 期间每笔资金按时间折算后的加权真实总成本）
    denominator = D(str(V0)) + weighted_cf

    # 5. 安全阀：拦截负分母或分母为 0
    if denominator <= 0:
        return {
            "success": True,
            "rate_of_return": None,
            "net_profit": numerator,
            "is_crazy_trader": True,
        }

    # 6. 正常输出标准迪茨法收益率（rate_of_return 转 float，net_profit 保留 Decimal）
    roi = (numerator / denominator) * 100
    return {
        "success": True,
        "rate_of_return": float(roi),
        "net_profit": numerator,
        "is_crazy_trader": False,
    }

