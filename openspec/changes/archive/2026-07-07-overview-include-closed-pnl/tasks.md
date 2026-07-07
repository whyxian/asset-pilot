## 1. 概览纳入已归档盈亏

- [x] 1.1 `overview_service.py` 在有 `txns` 的分支中，查询 closed_holdings 的 `realized_pnl` 追加到 `daily_flows`
- [x] 1.2 `start_date` 扩展到 `min(最早交易日期, 最早清仓日期)`
- [x] 1.3 适配无 `txns` 但有关闭持仓的场景（`else` 分支）

## 2. 验证

- [x] 2.1 运行 pytest 确认无回归
- [x] 2.2 更新 `openspec/specs/overview/spec.md`（纳入 MODIFIED 内容）
