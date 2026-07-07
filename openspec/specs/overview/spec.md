# 概览统计（Overview）

## Requirements

### Requirement: OverviewStats 包含累计收益率

概览接口返回 `OverviewStats`，其中 `cumulative_return_pct` 字段表示 Modified Dietz 总收益率百分比（非年化），与 `cumulative_return`（金额）成对。

#### Scenario: API 返回累计收益率

- **WHEN** 前端请求 `GET /api/v1/overview`
- **THEN** 返回 JSON 中包含 `cumulative_return_pct`（float，百分比）和 `cumulative_return`（金额）
