# AssetPilot 需求文档

> 版本：v2.0（按前端页面结构重新组织）
> 最后更新：2026-06-07

---

## 1. 项目概述

个人投资看板与净值计算器，覆盖股票、基金两类资产，跨 A股、美股、加密货币三大市场。
以**持仓为主、交易为辅**，提供持仓管理、盈亏计算、简单年化回报率分析、净值走势追踪的核心功能。

## 2. 资产分类

| 类别 | 说明 | 示例 |
|------|------|------|
| 股票 | 个股，包括 A股、美股 | 600519、AAPL |
| 基金 | ETF、LOF 等场内基金，按金额申购 | 166002、110011 |

> 市场维度（A/US/CRYPTO）是行情来源，资产类别（STOCK/FUND）是业务分类，两者正交。

## 3. 页面功能

### 3.1 概览页（`/`）

组合级别的数据总览：

- **统计卡**：总市值、总成本、总盈亏（金额 + 百分比）、简单年化回报率
  - 数据来源：持仓 + 实时行情，页面渲染时实时计算
  - 总市值 = Σ(持仓量 × 最新价)
  - 总盈亏% = (总市值 / 总成本 - 1) × 100
  - 年化回报率 = 按市值加权各品种的年化回报率
- **净值走势图**：时间轴折线图，展示市值 vs 成本的变化
  - 数据来源：networth_snapshots 表（快照）
- **资产配比**：按市场（A/US/CRYPTO/FUND）分组的市值占比，横向条形图或饼图

### 3.2 持仓页（`/holdings`）

当前所有持仓品种的明细表格：

| 列 | 说明 | 计算方式 |
|----|------|---------|
| 代码 | ticker | 直接存储 |
| 名称 | name | 直接存储 |
| 市场 | market | A / US / CRYPTO / FUND |
| 持仓量 | quantity | 直接存储 |
| 成本价 | cost_price | 加权平均成本，定投入
| 现价 | current_price | **实时计算**：从行情接口获取最新价 |
| 市值 | market_value | **实时计算**：quantity × current_price |
| 盈亏额 | pnl | **实时计算**：market_value − total_invested |
| 盈亏% | pnl_pct | **实时计算**：(market_value / total_invested − 1) × 100 |
| 年化回报率 | annualized_return | **实时计算**：(current_price / cost_price)^(1/holding_years) − 1 |

**功能点：**
- 新增/编辑/删除持仓品种
- 持仓字段：ticker、name、market、asset_class、currency、quantity、cost_price、total_invested、first_buy_date
- 持仓量 ≤ 0 的品种自动标记为已清仓，可选择隐藏

**年化回报率公式：**
```
持有年数 = (当前日期 − first_buy_date) / 365
年化回报率 = (current_price / cost_price) ^ (1 / holding_years) − 1
```
- first_buy_date 为空时无法计算 → 返回 None
- cost_price 为 0 时无法计算 → 返回 None

### 3.3 交易记录页（`/transactions`）

**描述：** 记录每笔买入/卖出操作，作为持仓变动的辅助记录。不强制使用。

**功能点：**
- 查看交易记录列表（按日期倒序）
- 新增交易记录（日期、品种、方向、数量、单价、金额、备注）
- 编辑/删除已有交易记录
- 支持按品种、时间范围筛选
- ~~手续费字段~~——未来优化项，当前不实现

**输入格式：**
```
date, ticker, type, quantity, unit_price, amount, notes
2024-01-05, 600519, buy, 100, 1650.00, 165000, 首次建仓
```

### 3.4 行情查询页（`/quotes`）

**描述：** 辅助工具，输入标的代码查询实时价格。

**功能点：**
- 输入框支持：A 股代码（600519）、美股代码（AAPL）、加密货币（BTC）、基金代码（166002）
- 查询后展示价格、涨跌额、涨跌幅、更新时间
- 数据直接来自行情 API，不存储

### 3.5 定投计划（规划中）

**描述：** 设定定期投资计划，按周期自动更新持仓。

**功能点（待实现）：**
- 创建定投计划：选择品种、定投金额、周期（每周/每月）、执行日期
- 按计划到期自动计算：新增持仓量 = 定投金额 / 当前净值
- 自动更新持仓表的 quantity、cost_price、total_invested

---

## 4. 已接入行情源

| 市场 | 数据源 | 方式 |
|------|--------|------|
| A 股 | 腾讯财经 HTTP API | httpx 异步请求 |
| 美股 | 新浪财经 + Playwright | 浏览器自动化 |
| 加密货币 | CoinGlass API | httpx 异步请求 |
| 基金 | 天天基金 pingzhongdata / akshare（备选） | httpx 异步请求 |

---

## 5. 技术栈

| 层 | 技术 |
|---|------|
| 后端框架 | FastAPI / Python 3.11 |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | SQLite (aiosqlite) |
| 前端 | React + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| 图表 | Recharts |
| 图标 | lucide-react |
| 状态管理 | Zustand + TanStack Query |
| 行情 HTTP 客户端 | httpx |
| 美股爬取 | Playwright (async API) |
