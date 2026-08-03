# AssetPilot 数据库设计

> 版本：v1.3
> 最后更新：2026-08-04（新增 cash_flows 资金流水表 + asset_holdings.cash_account_enabled）

---

## 1. 设计原则

- 持仓是直接维护的事实源，交易记录作为辅助记录
- 价格数据持久化存储，支持历史净值曲线回溯
- 资产主表统一管理所有可交易品种

## 2. 表结构

> 所有表默认包含以下审计字段，各表描述中不再单独列出：
> - `created_at TIMESTAMP` — 创建时间
> - `created_by VARCHAR(100)` — 创建人
> - `updated_at TIMESTAMP` — 更新时间
> - `updated_by VARCHAR(100)` — 更新人

### 2.1 asset_varieties（资产品种表）

所有可交易的标的，包括股票、基金等。创建持仓前必须先在此表中注册品种，用于校验输入有效性。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| ticker | VARCHAR(30) | NOT NULL, INDEX | 交易代码，如 "600519" / "AAPL" / "510050" |
| name | VARCHAR(200) | NOT NULL | 名称，如 "贵州茅台" / "Apple Inc" |
| market | VARCHAR(10) | NOT NULL | 市场，"CN" / "US" / "CRYPTO" |
| asset_class | VARCHAR(10) | NOT NULL | 资产类别，"STOCK" / "FUND" |
| sub_category | VARCHAR(20) | NULLABLE | 细分种类，"ETF" / "LOF" 等，默认为空 |
| currency | VARCHAR(3) | NOT NULL DEFAULT 'USD' | 计价货币，"CNY" / "USD" |
| is_active | BOOLEAN | DEFAULT 1 | 软删除标记 |

约束：`UNIQUE(asset_class, market, ticker)` — 同一只标的可在不同市场/类别下出现（如 000001 同时是 A 股银行股和深交所基金）。

索引：
- `ix_asset_varieties_ticker` ON (ticker)

### 2.2 asset_holdings（持仓表）

记录当前持仓状态。派生字段（quantity / cost_price / total_invested）由 `recompute_holding` 从 0 起点回放该品种全部交易记录算出——交易记录是唯一现金流事实源（为 XIRR 铺路）。建仓时自动生成一笔 buy 交易，持仓页手动改份额/成本自动生成勘误交易（日期=建仓日）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| ticker | VARCHAR(30) | NOT NULL, UNIQUE | 标的代码，如 "600519" / "AAPL" / "166002" |
| name | VARCHAR(200) | NOT NULL DEFAULT '' | 名称 |
| market | VARCHAR(10) | NOT NULL | 市场，"CN" / "US" / "CRYPTO" |
| asset_class | VARCHAR(10) | NOT NULL | 资产类别，"STOCK" / "FUND" / "CRYPTO" |
| currency | VARCHAR(3) | NOT NULL DEFAULT 'CNY' | 计价货币 |
| quantity | DECIMAL(18,4) | NOT NULL | 持仓量（recompute 算出） |
| cost_price | DECIMAL(18,4) | NOT NULL | 加权平均成本价（recompute 算出） |
| total_invested | DECIMAL(18,4) | NOT NULL | 总投入金额（recompute 算出） |
| first_buy_date | DATE | NOT NULL | 首次买入日期（建仓交易决定，不可改） |
| liquidated_at | DATE | NULLABLE | 清仓日期（recompute 写入，归档后行被搬走） |
| cash_account_enabled | BOOLEAN | NOT NULL DEFAULT 0 | 建仓时资金来源：勾选=从现金余额扣款（校验余额），不勾选=自动先入金等额（历史本金）。现金追踪本身永远开，该字段只影响建仓当次 |

约束：UNIQUE(asset_class, market, ticker)

### 2.3 asset_snapshots（品种快照表）✅ 已创建

每次手动触发记录每个品种当时的持仓状态。原币和 USD 双存：原币便于审计，USD 便于聚合。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| snapshot_date | DATE | NOT NULL, INDEX | 快照日期 |
| ticker | VARCHAR(30) | NOT NULL, INDEX | 标的代码 |
| asset_class | VARCHAR(10) | NOT NULL | 资产类别 |
| market | VARCHAR(10) | NOT NULL | 市场 |
| name | VARCHAR(200) | | 品种名 |
| currency | VARCHAR(3) | | 该品种原币 |
| quantity | DECIMAL(18,4) | NOT NULL | 持仓数量 |
| unit_value | DECIMAL(18,4) | NOT NULL | 现价（原币） |
| cost_value | DECIMAL(18,4) | NOT NULL | 成本价（原币） |
| market_value | DECIMAL(18,4) | NOT NULL | 市值（原币） |
| market_value_usd | DECIMAL(18,4) | NOT NULL | 市值（USD） |
| total_invested | DECIMAL(18,4) | NOT NULL | 总投入（原币） |
| total_invested_usd | DECIMAL(18,4) | NOT NULL | 总投入（USD） |
| unrealized_pnl | DECIMAL(18,4) | NOT NULL | 浮动盈亏（原币） |
| return_pct | DECIMAL(10,4) | | 盈亏率 |
| created_at / updated_at / created_by / updated_by | | | 审计字段 |

约束：UNIQUE(asset_class, market, ticker, snapshot_date)

### 2.4 networth_snapshots（净资产快照）✅ 已创建

组合级日快照，是 asset_snapshots 同日的预聚合（物化视图）。
**以 USD 为基准存储 + 冻结当日汇率**：历史曲线按当时汇率换算到目标币种，反映"那一刻"的真实价值。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| snapshot_date | DATE | NOT NULL, UNIQUE | 快照日期 |
| total_value_usd | DECIMAL(18,4) | NOT NULL | 总市值（USD） |
| total_cost_usd | DECIMAL(18,4) | NOT NULL | 总成本（USD） |
| total_pnl_usd | DECIMAL(18,4) | NOT NULL | 总盈亏（USD） |
| total_pnl_pct | DECIMAL(10,4) | | 盈亏率（零成本时 NULL） |
| annualized_return | DECIMAL(10,6) | | 加权年化（零成本时 NULL） |
| allocation | TEXT | NOT NULL | JSON: `[{market, label, value_usd, pct}]` |
| fx_rates | TEXT | NOT NULL | JSON: 快照时汇率，如 `{"CNY": 7.2, "HKD": 7.8}` |
| created_at / updated_at / created_by / updated_by | | | 审计字段 |

策略：当日重复触发会 INSERT OR REPLACE 覆盖。


### 2.5 transactions（交易记录表）✅ 已创建

每一笔买入/卖出操作，是现金流的唯一事实源（为 XIRR 铺路）。建仓时自动生成一笔 buy 交易（notes="建仓"），持仓页手动改份额/成本自动生成勘误交易（notes="手动调整:..."，日期=建仓日）。recompute_holding 从 0 起点回放该品种全部交易反推持仓派生字段。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| ticker | VARCHAR(30) | NOT NULL | 标的代码 |
| asset_class | VARCHAR(10) | NOT NULL | 资产类别 |
| market | VARCHAR(10) | NOT NULL | 市场 |
| transaction_date | DATE | NOT NULL | 交易日期 |
| type | VARCHAR(4) | NOT NULL, CHECK('buy','sell') | 方向，买入/卖出 |
| quantity | DECIMAL(18,4) | | 数量（可空，改成本勘误交易为 0） |
| unit_price | DECIMAL(18,4) | | 成交价（可空） |
| amount | DECIMAL(18,4) | | 交易金额（amount 优先，否则 quantity × unit_price） |
| notes | VARCHAR(500) | | 备注（"建仓"/"手动调整:..."等） |

约束：quantity 和 unit_price 至少填一个，或 amount 必填其一。

### 2.6 asset_quote（资产报价表）

每次抓取写入一条记录，记录某个品种在某个时间点的价格。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| ticker | VARCHAR(30) | NOT NULL | 标的代码 |
| timestamp | TIMESTAMP | NOT NULL | 价格时间点 |
| price | DECIMAL(18,4) | NOT NULL | 最新价 |
| change_price | DECIMAL(18,4) | | 涨跌额 |
| change_ratio | DECIMAL(10,4) | | 涨跌幅（%） |
| source | VARCHAR(30) | NOT NULL | 数据来源，"TENCENT" / "SINA" / "COINGLASS" |

约束：UNIQUE(asset_class, market, ticker, timestamp)（ORM 中暂未强制，已知技术债 #1）

### 2.7 closed_holdings（归档持仓表）

清仓后归档的完整持仓周期。realized_pnl = sum(sell.amount) - sum(buy.amount)（建仓投入通过 buy 交易体现）。pnl_pct 用 Modified Dietz 在归档时计算（建仓金额 V0，末笔卖出 V1，中间交易 CF），不受做 T 干扰。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| ticker | VARCHAR(30) | NOT NULL | 标的代码 |
| name | VARCHAR(200) | | 品种名 |
| market | VARCHAR(10) | NOT NULL | 市场 |
| asset_class | VARCHAR(10) | NOT NULL | 资产类别 |
| currency | VARCHAR(3) | | 计价货币 |
| total_buy_amount | DECIMAL(18,4) | NOT NULL | 该周期总买入金额（sum(buy.amount)） |
| first_buy_date | DATE | NOT NULL | 首次买入日期 |
| closed_at | DATE | NOT NULL | 清仓日期 |
| holding_days | INTEGER | NOT NULL | 持仓天数 |
| realized_pnl | DECIMAL(18,4) | NOT NULL | 已实现盈亏 = sum_sell - sum_buy |
| pnl_pct | DECIMAL(8,4) | | Modified Dietz 收益率百分比（归档时计算） |
| is_crazy_trader | BOOLEAN | NOT NULL DEFAULT 0 | 分母≤0 零成本持有标记 |

### 2.8 closed_transactions（归档交易表）

归档时把该周期的全部 transactions 复制到此表，原表删除。关联 closed_holdings.id。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| closed_holding_id | INTEGER | FK → closed_holdings.id | 关联归档持仓 |
| ticker | VARCHAR(30) | NOT NULL | 标的代码 |
| asset_class | VARCHAR(10) | NOT NULL | 资产类别 |
| market | VARCHAR(10) | NOT NULL | 市场 |
| transaction_date | DATE | NOT NULL | 交易日期 |
| type | VARCHAR(10) | NOT NULL | buy / sell |
| quantity | DECIMAL(18,4) | | 数量 |
| unit_price | DECIMAL(18,4) | | 成交价 |
| amount | DECIMAL(18,4) | | 交易金额 |
| notes | VARCHAR(500) | | 备注 |
| original_id | INTEGER | | 原 transactions.id（审计追溯） |

### 2.9 cash_flows（资金流水表）✅ 已创建

记录所有资金进出，独立于 transactions 表，是现金余额的事实源。买卖交易自动联动生成流水：新建 buy 交易 → 生成扣款流水（校验余额）；新建 sell 交易 → 生成入账流水；更新/删除交易 → 同步更新/删除关联流水。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| type | VARCHAR(10) | NOT NULL | 流水类型：`deposit`（入金）/ `withdraw`（出金）/ `buy`（买入扣款）/ `sell`（卖出入账） |
| amount | DECIMAL(18,4) | NOT NULL | 金额，正=入账（deposit/sell），负=出账（withdraw/buy） |
| currency | VARCHAR(3) | NOT NULL | 币种，如 "CNY" / "USD" |
| transaction_id | INTEGER | FK → transactions.id, NULLABLE, INDEX | buy/sell 时关联交易记录；deposit/withdraw 时为 NULL |
| notes | VARCHAR(500) | | 备注（建仓自动入金/扣款等） |

约束：withdraw 出金时校验同币种余额充足；删除归档持仓时连带删除关联的 cash_flows（通过 `closed_transactions.original_id` 回溯原 transactions.id，只删有 transaction_id 的 buy/sell 流水，自动入金流水保留）。

> 注意：归档时原 transactions 行被删，`transaction_id` 成为悬空引用（SQLite 默认不强制 FK）。现金余额不受影响——流水仍在，仅失去与归档交易的直接关联。

## 3. E-R 关系

```
asset_holdings                          当前持仓（三元组唯一，派生字段由 recompute 从交易回放）
       │
       │ 1
       N
   transactions ──→ cash_flows         交易记录（唯一现金流事实源，建仓自动生成 buy）
       │              buy/sell 自动联动生成流水（transaction_id 关联）
       │ 清仓归档
       ↓
   closed_holdings ──→ closed_transactions   归档持仓周期 + 归档交易（原表删除，original_id 追溯）
                                                     │ 删除归档持仓时经 original_id
                                                     ↓ 连带删除关联 buy/sell 流水
                                                 cash_flows    （deposit/withdraw 独立记录，不入归档）

asset_holdings ──→ asset_quote         行情记录（按三元组+ticker 关联）
       │
       │ N
asset_snapshots                         品种级日快照

networth_snapshots                      组合级日快照（独立）
```
