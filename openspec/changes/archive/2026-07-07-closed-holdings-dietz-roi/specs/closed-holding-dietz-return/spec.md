## ADDED Requirements

### Requirement: 已清仓持仓使用 Modified Dietz 计算收益率

系统 SHALL 在归档已清仓持仓时，使用 `calculate_modified_dietz` 计算该完整持仓周期的收益率，并存储到 `closed_holdings` 表。

- 参数字段：`V0=0`，`V1=0`，`trade_flows` 为该周期全部交易（buy 为正，sell 为负），`start_date`=首买日，`end_date`=清仓日
- 存储结果包含：`pnl_pct`（收益率百分比，float）和 `is_crazy_trader`（分母 ≤ 0 时标记）
- `pnl_pct` 使用 `round(x, 2)` 保留两位小数（同 active holdings）

#### Scenario: 正常持仓周期归档计算

- **WHEN** 持仓完成完整周期（买 → 卖光），触发归档
- **THEN** 归档时使用 `calculate_modified_dietz` 计算盈亏率，`pnl_pct` 为正确百分比值（如盈利 20%），`is_crazy_trader` 为 false

#### Scenario: 做T导致零成本持有归档

- **WHEN** 持仓经过做T操作后成本归零（分母 ≤ 0），触发归档
- **THEN** Modified Dietz 的 `denominator <= 0`，`pnl_pct` 为 null，`is_crazy_trader` 为 true

#### Scenario: 多次买卖的分批清仓归档

- **WHEN** 持仓经过多次买卖后清理（如买入→卖出50%→买入→卖出50%→清仓），触发归档
- **THEN** Modified Dietz 通过时间权重正确计算收益率，中间做T操作不干扰结果

### Requirement: 前端展示历史持仓盈亏率

系统 SHALL 从 API 的 `ClosedHolding` 字段中读取 `pnl_pct` 和 `is_crazy_trader`，按规则展示：

| `pnl_pct` | `is_crazy_trader` | 展示 |
|:---------:|:------------------:|------|
| 数值 | false | `formatPct(pnl_pct)`（如 +20.00%） |
| null | false | N/A |
| 任意值 | true | `--%`（灰色文本） |

#### Scenario: 正常显示收益率

- **WHEN** `pnl_pct=20.5`，`is_crazy_trader=false`
- **THEN** 前端显示 `+20.50%`，颜色按盈亏正负（红涨绿跌）

#### Scenario: Crazy trader 显示 "--%"

- **WHEN** `is_crazy_trader=true`
- **THEN** 前端显示 `--%`，用灰色次强调色

#### Scenario: 数据异常显示 N/A

- **WHEN** `pnl_pct=null`，`is_crazy_trader=false`
- **THEN** 前端显示 `N/A`，用灰色次强调色

### Requirement: 历史持仓详情弹窗展示一致

详情弹窗（`ClosedHoldingDetailDialog`）的盈亏率展示逻辑 MUST 与列表页一致，使用相同的取值和展示规则，不再 inline 计算。

#### Scenario: 详情弹窗盈亏率展示

- **WHEN** 用户在历史持仓列表点击"查看详情"
- **THEN** 弹窗中的盈亏率展示与列表页一致（`pnl_pct` + `is_crazy_trader` 规则）

### Requirement: 后端查询兼容已有数据

系统 SHALL 在查询已归档数据时，对 `pnl_pct` 和 `is_crazy_trader` 为 NULL 的行不做特殊处理（前端展示为 N/A 和 false）。

#### Scenario: 查询存量数据

- **WHEN** 查询已存在的归档记录（之前版本归档的，pnl_pct 和 is_crazy_trader 皆为 NULL）
- **THEN** `pnl_pct` 返回 null，`is_crazy_trader` 返回 false，前端正常展示 N/A
