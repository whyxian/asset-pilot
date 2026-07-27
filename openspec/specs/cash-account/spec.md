# 现金账户管理

## Requirements

### Requirement: 现金流水记录

系统 SHALL 提供 `cash_flows` 表存放资金流水，支持 deposit / withdraw / buy / sell 四种类型。
每笔流水记录金额、币种、关联交易 ID（可选）和备注。

#### Scenario: 入金

- **WHEN** 用户调用 `POST /api/v1/cash/deposit` 入金 $2000
- **THEN** cash_flows 新增一条 type=deposit, amount=+2000, currency=USD 的记录

### Requirement: 买卖联动现金

系统 SHALL 在建仓时设定 `cash_account_enabled`，启用后 buy 扣现金、sell 加现金、delete 回退。

#### Scenario: 现金充足时买入

- **WHEN** USD 现金余额为 $2000，买入 $1000 的股票（cash_account_enabled=true）
- **THEN** 交易成功，cash_flows 新增 type=buy, amount=-1000，USD 余额变为 $1000

#### Scenario: 现金不足时买入

- **WHEN** USD 现金余额为 $500，买入 $1000 的股票（cash_account_enabled=true）
- **THEN** 买入被拒绝，返回余额不足错误

### Requirement: 现金余额查询

系统 SHALL 提供余额查询接口，按币种汇总 amount 之和。

#### Scenario: 查询余额

- **WHEN** 用户调用 `GET /api/v1/cash/balances`
- **THEN** 返回各币种余额列表，如 [{currency: "USD", balance: 2500}, {currency: "CNY", balance: 80000}]

### Requirement: 现金流水显示

系统 SHALL 提供前端页面 `/cash` 展示余额卡片和流水列表。

#### Scenario: 现金页显示

- **WHEN** 用户点击侧边栏"现金"
- **THEN** 显示余额卡片（分币种 + 总资产）和流水列表（时间倒序）
