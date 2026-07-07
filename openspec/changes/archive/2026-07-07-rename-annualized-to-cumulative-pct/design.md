## Context

概览页 API 返回 `OverviewStats` 中有一个字段叫 `annualized_return`，实际存的是 Modified Dietz 总收益率（float 百分比），不是年化。前端卡片标题是"历史累计总收益"——百分比字段应与金额字段 `cumulative_return` 成对。

## Changes

纯改名，不改逻辑。5 个文件同步修改：

| 层 | 文件 | old → new |
|---|---|---|
| Pydantic model | `overview.py` | `annualized_return: float \| str \| None` → `cumulative_return_pct` |
| Service | `overview_service.py` | `avg_annualized` → `total_return_pct` |
| Frontend type | `types/index.ts` | `annualized_return` → `cumulative_return_pct` |
| Frontend UI | `OverviewPage.tsx` | `stats.annualized_return` → `stats.cumulative_return_pct` |
| Test | `test_overview_service.py` | `result.annualized_return` → `result.cumulative_return_pct` |
