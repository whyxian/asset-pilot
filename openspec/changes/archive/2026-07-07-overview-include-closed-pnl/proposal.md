## Why

概览 Modified Dietz 只用了 `transactions` 表中的未归档交易，已归档持仓（`closed_holdings`）的已实现盈亏被忽略。导致：
1. 删除历史持仓后概览数字不变（假象）
2. 更重要的是，历史持仓的盈亏从未被计入总体回报率——数据真实失真

## What Changes

- 概览 Modified Dietz 的现金流（CF）追加已归档持仓的 `-realized_pnl`
- 日期用 `closed_at`（清仓日），时间权重自动调整
- `start_date` 扩展到 `min(最早交易日期, 最早清仓日期)`

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `overview`：概览 Modified Dietz 计算纳入历史持仓已实现盈亏

## Impact

- `overview_service.py`：追加 closed_holdings 的现金流
- `openspec/specs/overview/spec.md`：更新需求（可选）
