# 概览统计（Overview）

## Requirements

### Requirement: OverviewStats 包含累计收益率

概览接口返回 `OverviewStats`，其中 `cumulative_return_pct` 字段表示 Modified Dietz 总收益率百分比（非年化），与 `cumulative_return`（金额）成对。

#### Scenario: API 返回累计收益率

- **WHEN** 前端请求 `GET /api/v1/overview`
- **THEN** 返回 JSON 中包含 `cumulative_return_pct`（float，百分比）和 `cumulative_return`（金额）

#### Scenario: 已归档盈亏纳入累计收益率

- **WHEN** 存在已归档持仓（`closed_holdings` 非空），且有 active holdings
- **THEN** Modified Dietz 的现金流中包含 `-realized_pnl × 汇率` 项（日期=closed_at），使历史盈利/亏损被计入总收益率

#### Scenario: 删除历史持仓后累计收益率变化

- **WHEN** 删除一条已归档持仓记录
- **THEN** 概览 `cumulative_return_pct` 反映该笔盈亏的移除
