## Why

概览页 `OverviewStats.annualized_return` 字段名是 "年化回报率" 的语义，但实际存的是 Modified Dietz 总收益率（从建仓至今的整体回报百分比，并非年化）。字段名与语义不匹配，容易误导后续开发者。

## What Changes

- `OverviewStats.annualized_return` → `cumulative_return_pct`，与 `cumulative_return`（金额）成对
- 对应变量名、类型名、前端消费点同步改名
- 不改动 `HoldingWithQuote.annualized_return`（独立问题，不在本 change 范围）

## Capabilities

### New Capabilities

（无新增能力）

### Modified Capabilities

- `overview`：`OverviewStats` 中 `annualized_return` 字段改名为 `cumulative_return_pct`，更新对应测试断言

## Impact

- **backend/app/models/overview.py**: `annualized_return` → `cumulative_return_pct`
- **backend/app/services/overview_service.py**: 变量名 `avg_annualized` → `total_return_pct`
- **frontend/src/types/index.ts**: `OverviewStats.annualized_return` → `cumulative_return_pct`
- **frontend/src/features/overview/OverviewPage.tsx**: `stats.annualized_return` → `stats.cumulative_return_pct`
- **backend/test/test_overview_service.py**: 测试断言改字段名
