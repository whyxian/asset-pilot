## 1. DB Schema — closed_holdings 表加字段

- [x] 1.1 `ClosedHoldingRecord` ORM 加 `pnl_pct`(Numeric(8,4), nullable) 和 `is_crazy_trader`(Boolean, default=false) 列
- [x] 1.2 `ClosedHolding` Pydantic 模型加对应字段（`pnl_pct: float | None = None`, `is_crazy_trader: bool = False`）
- [x] 1.3 `_record_to_closed_holding()` 映射新字段

## 2. 归档时计算 Modified Dietz

- [x] 2.1 在 `archive_holding()` 中遍历 `txns` 构造 `trade_flows`（buy 正/sell 负，含日期和金额）
- [x] 2.2 调用 `calculate_modified_dietz(V0=0, V1=0, trade_flows, start_date=first_buy_date, end_date=closed_at)`
- [x] 2.3 将 result 的 `rate_of_return` 和 `is_crazy_trader` 写入 `ClosedHoldingRecord`

## 3. 前端历史持仓列表

- [x] 3.1 `HistoryPage.tsx` 删除 `pnlPct()` 函数（`toNum()` 保留，因 `realized_pnl` 颜色判断和详情页数量格式化仍需使用）
- [x] 3.2 表格 "盈亏率" 列改读 `h.pnl_pct`，按 `h.is_crazy_trader` 判断是否显示 `--%`
- [x] 3.3 前端 TypeScript 类型 `ClosedHolding` 新增 `pnl_pct` 和 `is_crazy_trader`

## 4. 前端历史持仓详情弹窗

- [x] 4.1 `ClosedHoldingDetailDialog.tsx` 删除 inline 除法 `toNum(data.realized_pnl) / toNum(data.total_buy_amount) * 100`
- [x] 4.2 改读 `data.pnl_pct`，按 `data.is_crazy_trader` 显示 `(--%)`

## 5. 验证

- [x] 5.1 pytest 95 tests passed 无回归
- [ ] 5.2 手动验证：触发一次归档，检查 `closed_holdings` 表新字段值正确
- [ ] 5.3 手动验证：存量数据（之前归档的）前端正常显示 N/A
