## 1. 后端改名

- [x] 1.1 `OverviewStats` Pydantic 模型 `annualized_return` → `cumulative_return_pct`
- [x] 1.2 `overview_service.py` 变量 `avg_annualized` → `total_return_pct`，赋值处同步

## 2. 前端改名

- [x] 2.1 `types/index.ts` `OverviewStats.annualized_return` → `cumulative_return_pct`
- [x] 2.2 `OverviewPage.tsx` 三处 `stats.annualized_return` → `stats.cumulative_return_pct`

## 3. 验证

- [x] 3.1 `test_overview_service.py` 测试断言改字段名
- [x] 3.2 运行 pytest 确认无回归
