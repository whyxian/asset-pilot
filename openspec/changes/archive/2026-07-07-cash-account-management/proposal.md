## Why

当前系统只能追踪持仓的买卖，无法管理资金账户。卖出股票后的资金"消失"了，个人收入/支出也无法记录。加入现金账户后：
- 买入股票从现金扣款，卖出股票资金回现金
- 支持个人收入（工资入金）和消费支出记账
- 概览总资产=现金余额+持仓市值

## What Changes

- 新建 `cash_flows` 表（独立于 `transactions`）记录资金流水
- `asset_holdings` 加 `cash_account_enabled` 字段（建仓时设定，不可改）
- 买入时校验现金余额 ≥ 买入金额，卖出/删除时同步回退现金
- 建仓弹窗加"从现金账户扣除"勾选框
- 前端新页面 `/cash`（余额卡片 + 流水列表 + 入金/出金操作）
- 侧边栏加"现金"菜单项

## Capabilities

### New Capabilities
- `cash-account`: 现金账户管理（资金流水 + 余额校验 + 买卖联动）

### Modified Capabilities

（无现有 specs 需要修改）

## Impact

- **DB**: 新建 `cash_flows` 表 + `asset_holdings.cash_account_enabled`
- **Backend**: CashFlow repository/service/api；TransactionService 联动校验和资金更新
- **Frontend**: 新页面 `/cash`；侧边栏菜单；建仓对话框加勾选框
