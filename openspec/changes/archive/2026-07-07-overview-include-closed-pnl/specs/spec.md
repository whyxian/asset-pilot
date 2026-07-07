## MODIFIED Requirements

### Requirement: 概览 Modified Dietz 纳入已归档盈亏

概览 Modified Dietz 的现金流构建需追加 `closed_holdings.realized_pnl`（以
`-realized_pnl` 形式，日期=closed_at），使历史持仓的已实现盈亏被计入总收益率。

#### Scenario: 删除历史持仓后总收益率变化
- **WHEN** 删除一条已归档的历史持仓
- **THEN** `GET /api/v1/overview` 的 `cumulative_return_pct` 不再包含该笔已实现盈亏

#### Scenario: 总收益率包含历史已实现盈亏
- **WHEN** 存在已归档持仓（realized_pnl > 0），且当前有 active holdings
- **THEN** Modified Dietz 的 net_profit = 当前市值 + 所有已归档 realized_pnl - 总投入
