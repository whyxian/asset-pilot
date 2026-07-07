# 已清仓持仓收益率（Closed Holding Dietz Return）

## Requirements

### Requirement: 已清仓持仓使用 Modified Dietz 计算收益率

系统 SHALL 在归档已清仓持仓时，使用 `calculate_modified_dietz` 计算该完整持仓周期的收益率，并存储到 `closed_holdings` 表。

- 参数：建仓金额为 V0，末笔卖出金额为 V1，中间交易为现金流（buy 正/sell 负）
- 存储结果包含：`pnl_pct`（收益率百分比，float）和 `is_crazy_trader`（分母 ≤ 0 时标记）

#### Scenario: 正常持仓周期归档计算

- **WHEN** 持仓完成完整周期（买 → 卖光），触发归档
- **THEN** 归档时使用 `calculate_modified_dietz` 计算盈亏率，`pnl_pct` 为正确百分比值（如盈利 20%），`is_crazy_trader` 为 false

#### Scenario: 做T导致零成本持有归档

- **WHEN** 持仓经过做T操作后成本归零（分母 ≤ 0），触发归档
- **THEN** Modified Dietz 的 `denominator <= 0`，`pnl_pct` 为 null，`is_crazy_trader` 为 true

### Requirement: 前端展示历史持仓盈亏率

系统 SHALL 从 API 的 `ClosedHolding` 字段中读取 `pnl_pct` 和 `is_crazy_trader`，按 `is_crazy_trader=true` 显示 `--%`、`pnl_pct=null` 显示 N/A 的规则展示。

#### Scenario: 正常显示收益率

- **WHEN** `pnl_pct=20.5`，`is_crazy_trader=false`
- **THEN** 前端显示 `+20.50%`

#### Scenario: Crazy trader 显示 "--%"

- **WHEN** `is_crazy_trader=true`
- **THEN** 前端显示 `--%`

### Requirement: 后端查询兼容已有数据

系统 SHALL 在查询已归档数据时，对 `pnl_pct` 和 `is_crazy_trader` 为 NULL 的行不做特殊处理。

#### Scenario: 查询存量数据

- **WHEN** 查询已存在的归档记录（pnl_pct 和 is_crazy_trader 皆为 NULL）
- **THEN** `pnl_pct` 返回 null，`is_crazy_trader` 返回 false
