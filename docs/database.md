# AssetPilot 数据库设计

> 版本：v1.1
> 最后更新：2026-06-10

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
| market | VARCHAR(10) | NOT NULL | 市场，"A" / "US" / "CRYPTO" |
| asset_class | VARCHAR(10) | NOT NULL | 资产类别，"STOCK" / "FUND" |
| currency | VARCHAR(3) | NOT NULL DEFAULT 'USD' | 计价货币，"CNY" / "USD" |
| is_active | BOOLEAN | DEFAULT 1 | 软删除标记 |

约束：`UNIQUE(asset_class, market, ticker)` — 同一只标的可在不同市场/类别下出现（如 000001 同时是 A 股银行股和深交所基金）。

索引：
- `ix_asset_varieties_ticker` ON (ticker)

### 2.2 asset_holdings（持仓表）

直接记录当前持仓状态，是持仓计算的事实源。定投等批量操作自动更新此表。
使用 ticker 直接作为品种标识，不通过 asset_varieties 外键关联。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| ticker | VARCHAR(30) | NOT NULL, UNIQUE | 标的代码，如 "600519" / "AAPL" / "166002" |
| name | VARCHAR(200) | NOT NULL DEFAULT '' | 名称 |
| market | VARCHAR(10) | NOT NULL | 市场，"A" / "US" / "CRYPTO" |
| asset_class | VARCHAR(10) | NOT NULL | 资产类别，"STOCK" / "FUND" |
| currency | VARCHAR(3) | NOT NULL DEFAULT 'CNY' | 计价货币 |
| quantity | DECIMAL(18,4) | NOT NULL | 持仓量 |
| cost_price | DECIMAL(18,4) | NOT NULL | 加权平均成本价 |
| total_invested | DECIMAL(18,4) | NOT NULL | 总投入金额 |
| first_buy_date | DATE | NOT NULL | 首次买入日期 |

约束：UNIQUE(ticker)

### 2.3 asset_snapshots（品种快照表）

每日定时计算并写入，记录每个品种当日的持仓状态，用于历史净值回溯。
数据来源：asset_holdings + 实时行情。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| snapshot_date | DATE | NOT NULL | 快照日期 |
| ticker | VARCHAR(30) | NOT NULL | 标的代码 |
| quantity | DECIMAL(18,4) | NOT NULL | 持仓数量 |
| unit_value | DECIMAL(18,4) | NOT NULL | 当日收盘价/净值 |
| cost_value | DECIMAL(18,4) | NOT NULL | 持仓总成本 |
| market_value | DECIMAL(18,4) | NOT NULL | 持仓市值 |
| unrealized_pnl | DECIMAL(18,4) | NOT NULL | 盈亏额 |
| return_pct | DECIMAL(10,4) | | 收益率（%） |

约束：UNIQUE(snapshot_date, ticker)

### 2.4 networth_snapshots（净资产快照）

每日组合级别的汇总。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| snapshot_date | DATE | NOT NULL, UNIQUE | 快照日期 |
| total_value | DECIMAL(18,4) | NOT NULL | 总市值 |
| total_cost | DECIMAL(18,4) | NOT NULL | 总成本 |
| total_pnl | DECIMAL(18,4) | NOT NULL | 总盈亏 |
| annualized_return | DECIMAL(10,6) | | 简单年化回报率 |

### 2.5 transactions（交易记录表）

每一笔买入/卖出操作，作为持仓变动的辅助记录。股票按数量+成交价录入，基金按金额录入。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTOINCREMENT | 主键 |
| ticker | VARCHAR(30) | NOT NULL | 标的代码 |
| transaction_date | DATE | NOT NULL | 交易日期 |
| type | VARCHAR(4) | NOT NULL, CHECK('buy','sell') | 方向，买入/卖出 |
| quantity | DECIMAL(18,4) | | 数量（股票必填，基金可空） |
| unit_price | DECIMAL(18,4) | | 成交价（股票必填，基金可空） |
| amount | DECIMAL(18,4) | | 交易金额（基金必填，股票自动计算） |
| notes | TEXT | | 备注 |

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

约束：UNIQUE(variety_id, timestamp)

## 3. E-R 关系

```
asset_holdings                          当前持仓（按 ticker 唯一，不关联品种表）
       │
       │
       1
       │
       N
   transactions                         交易记录（辅助，按 ticker 关联持仓）
   
asset_holdings ──→ asset_quote         价格记录（按 ticker 关联）
       │
       │
       N
asset_snapshots                         每日快照

networth_snapshots                      组合级汇总（独立）
```
