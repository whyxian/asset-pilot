## Context

在已有持仓/交易系统上增加现金账户层，实现资金流闭环。

### 核心设计理念

```
外部收入 → cash_flows(deposit) → 现金余额
现金余额 → cash_flows(buy) → 持仓
持仓 → cash_flows(sell) → 现金余额
现金余额 → cash_flows(withdraw) → 外部支出
```

`asset_holdings.cash_account_enabled` 控制该持仓是否参与现金流转（建仓时设定）。

## DB 结构

### cash_flows 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| type | VARCHAR(10) | NOT NULL | deposit / withdraw / buy / sell |
| amount | DECIMAL(18,4) | NOT NULL | 正=入账，负=出账 |
| currency | VARCHAR(3) | NOT NULL | 币种 |
| transaction_id | INTEGER | FK → transactions.id, nullable | buy/sell 时关联 |
| notes | VARCHAR(500) | | 备注（历史导入时="历史导入自动入账"） |
| created_at | DATETIME | | |
| updated_at | DATETIME | | |
| created_by | VARCHAR(100) | | |
| updated_by | VARCHAR(100) | | |

### asset_holdings 加字段

`cash_account_enabled: Boolean, default false, nullable false` — 建仓时设定，不可改

## 后端改动

### 新层：CashFlowRepository + CashFlowService + API

- `GET /api/v1/cash/balances` → 各币种余额（汇总 amount）
- `GET /api/v1/cash/flows?limit=50` → 流水列表（倒序）
- `POST /api/v1/cash/deposit` → 入金
- `POST /api/v1/cash/withdraw` → 出金
- `DELETE /api/v1/cash/flows/{id}` → 删除一笔流水

余额计算：`SELECT currency, SUM(amount) FROM cash_flows GROUP BY currency`

### TransactionService 联动

**新增交易时（cash_account_enabled=true）：**
- buy: 查 `cash_flows` 中该币种余额 ≥ buy 金额，写入一条 type=buy 的 cash_flow（金额为负）
- sell: 写入一条 type=sell 的 cash_flow（金额为正）

**修改交易时（cash_account_enabled=true）：**
- 同事务内同步更新关联 cash_flow 的 amount

**删除交易时（cash_account_enabled=true）：**
- 同事务内删除关联 cash_flow 记录

**历史导入（cash_account_enabled=false）：**
- 不做任何 cash_flow 操作

### 建仓时设定 cash_account_enabled

`POST /api/v1/holdings` 新增可选参数 `cash_account_enabled=false`，建仓后不可修改（PUT 时忽略该字段）。

## 前端改动

### 新页面 /cash

```
现金管理
├── 余额卡片（每个币种一张 + 总资产（默认币种，含持仓市值））
│   └── USD: $2,500 / CNY: ¥80,000 / 总资产: ¥XX,XXX
├── 操作按钮
│   ├── [+入金] → 弹窗：金额 + 币种 + 备注
│   └── [-出金] → 弹窗：金额 + 币种 + 备注
└── 流水列表（时间倒序）
    ├── 日期 | 类型 | 金额 | 备注
    ├── 入金类型用绿色，出金用红色
    └── buy/sell 可点击跳转到关联交易
```

### 侧边栏

导航菜单加"现金"项，路径 `/cash`，图标 `Wallet`

### 建仓对话框

加一个勾选框 `□ 从现金账户扣除`，默认勾选。
- 勾选时：`cash_account_enabled=true`，买入时校验现金余额
- 不勾选时：`cash_account_enabled=false`，跳过现金操作

## 风险 / 未定

- 汇率用概览已有的 `fetch_rates`，避免重复获取
- 总资产 = 现金余额(USD) + 持仓市值(USD)，按 `?currency=` 换算
