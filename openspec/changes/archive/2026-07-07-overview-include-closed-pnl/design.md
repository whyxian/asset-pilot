## Context

概览 Modified Dietz 只从 `transactions` 表提取现金流，已归档的盈利/亏损被完全排除。修复后：

- closed_holdings 的 `realized_pnl` 以 `-realized_pnl` 形式追加到 CF（日期=closed_at）
- 已归档现金流的币种换算与现有逻辑一致（`convert_with_rates`）
- start_date 取 `min(最早交易日期, 最早清仓日期)` 确保时间范围正确

```python
# 在现有 daily_flows 构建后追加：
for ch in closed_list:
    amount = -ch.realized_pnl           # 盈利→负（钱从系统回流）
    amount_usd = convert_with_rates(amount, ch.currency, "USD", rates)
    daily_flows[str(ch.closed_at)] += amount_usd

start_date = min(
    min(t.transaction_date for t in txns) if txns else today,
    min(ch.closed_at for ch in closed_list) if closed_list else today,
)
```
