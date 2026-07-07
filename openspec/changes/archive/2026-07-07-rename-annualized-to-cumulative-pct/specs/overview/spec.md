## MODIFIED Requirements

### Requirement: OverviewStats includes cumulative return percentage

`OverviewStats` 模型的 `annualized_return` 字段改名为 `cumulative_return_pct`，语义从"年化回报率"修正为"总收益率百分比"，与 `cumulative_return`（金额）成对。

#### Scenario: API 返回新字段名

- **WHEN** 前端请求 `GET /api/v1/overview`
- **THEN** 返回 JSON 中 `annualized_return` 被替换为 `cumulative_return_pct`，值不变
