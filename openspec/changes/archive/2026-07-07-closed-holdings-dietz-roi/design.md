## Context

当前历史持仓盈亏率在前端用 `realized_pnl / total_buy_amount` 计算。做T操作使 `total_buy_amount` 膨胀（T 接回的成本计入分母），拉低盈利率。改用 Modified Dietz 能在归档时就算出并存储收益率，前端直接读取展示。

## Goals / Non-Goals

**Goals:**
- 已清仓持仓的盈亏率改用 Modified Dietz 在归档时计算，结果存入 `closed_holdings` 表
- `is_crazy_trader=True` 时前端展示 `--%`
- 历史持仓列表和详情页的 inline 除法计算删除，改读 API 字段

**Non-Goals:**
- 不修改 active holdings 的盈亏率计算
- 不改动概览页 Modified Dietz 的使用（那是组合级，这里是个股级）
- 不改动 `calculate_modified_dietz` 函数本身的逻辑（已修复）

## Decisions

### 计算时机：归档时（不在查询时）

在 `archive_holding()` 中计算，而非查询时动态算。理由：
- 归档时全部交易数据已在内存（`txns`），零额外 IO
- Modified Dietz 遍历 O(n)，n=该周期交易数，归档时走一次就够了
- 查询时动态算需要每次 Join `closed_transactions`，反范式化违背"只读快速"的设计

### Modified Dietz 参数

```
V0 = 0          # 建仓前市值 = 0
V1 = 0          # 清仓后市值 = 0
trade_flows     # 该周期全部交易，金额按系统惯例（buy 为正，sell 为负）
start_date      = first_buy_date
end_date        = closed_at
```

**推导：**
```
ROI = (V1 - V0 - total_cf) / (V0 + weighted_cf) × 100%
    = (-total_cf) / (weighted_cf) × 100%
```

其中 `total_cf < 0`(盈利) → `ROI > 0`；`total_cf > 0`(亏损) → `ROI < 0`。时间权重使做T的同日买入/卖出自然对冲。

### 存储：2 列

`closed_holdings` 表加：

| 列名 | 类型 | 说明 |
|------|------|------|
| `pnl_pct` | Numeric(8,4), nullable | 收益率百分比，如 20.50 表示 20.5% |
| `is_crazy_trader` | Boolean | Modified Dietz 分母 ≤ 0（零成本/负成本持有） |

`realized_pnl`（净利润金额）保持不动——它跟 Modified Dietz 的 `net_profit` 等价，前端还需金额展示。

### 前端展示规则

| `pnl_pct` | `is_crazy_trader` | 展示 |
|:---------:|:-------------------:|------|
| 20.5 | false | +20.50% |
| -5.0 | false | -5.00% |
| null | false | N/A |
| null/任意值 | true | --% (灰色) |

被标记为 crazy trader 时 `pnl_pct` 是多少都展示 `--%`，因为此时的分母没有经济意义，任何百分比数字都是误导。

## Risks / Trade-offs

- **[兼容性]** 现有已归档的历史持仓没有 `pnl_pct` 和 `is_crazy_trader` 值 → 回填为 NULL，前端走当前行为（显示 N/A）。后续新归档的持仓才会有正确值。
- **[精度]** Modified Dietz 的 `net_profit` 与现有 `realized_pnl` 可能因 Decimal/float 转换有极小精度差异（< 0.01 USD）。必要时在归档时统一用 `realized_pnl` 覆盖 Dietz 的 `net_profit`。
