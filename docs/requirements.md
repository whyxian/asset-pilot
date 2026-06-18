# AssetPilot 需求文档

> 版本：v2.4
> 最后更新：2026-06-19

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

### 3.1 概览页（`/`）✅ 已实现

组合级别的数据总览：

- ✅ **统计卡**：总市值、总成本、总盈亏（金额 + 百分比）、市值加权年化回报率
  - 数据来源：`GET /api/v1/overview`（后端聚合 + 汇率换算）
- ✅ **净值走势图**：Recharts 折线图（基于 networth_snapshots 快照）
- ✅ **资产配比**：按 market（CN/US/CRYPTO）分组的市值占比，进度条展示
- ✅ **手动刷新**：刷新按钮强制拉最新行情（force_refresh=true 绕过基金 15min 缓存）

### 3.2 持仓页（`/holdings`）✅ 已实现

当前所有持仓品种的明细表格：

| 列 | 说明 | 计算方式 |
|----|------|---------|
| 代码 | ticker | 直接存储 |
| 名称 | name | 直接存储 |
| 市场 | market | CN / US / CRYPTO |
| 持仓量 | quantity | 直接存储 |
| 成本价 | cost_price | 加权平均成本 |
| 现价 | current_price | **实时计算**：`GET /api/v1/holdings/with-quotes` |
| 市值 | market_value | **实时计算**：quantity × current_price |
| 盈亏 | pnl_pct | **实时计算**：(market_value / total_invested − 1) × 100 |
| 年化回报率 | annualized_return | **实时计算**：(current_price / cost_price)^(1/holding_years) − 1 |

**功能点：**
- ✅ 查看持仓列表（含实时行情 + 计算字段）
- ✅ 新增持仓（对话框表单，自动联动市场→货币、数量×单价→总投入）
- ✅ 编辑持仓（内联编辑，ticker/market/asset_class 不可改）
- ✅ 删除持仓（确认横幅）
- ✅ 手动刷新（force_refresh=true 强制拉最新行情，绕过基金 15min 缓存）
- ✅ 加载态（骨架屏）、错误态（重试）、空态（引导按钮）

**年化回报率公式：**
```
持有年数 = (当前日期 − first_buy_date) / 365
年化回报率 = (current_price / cost_price) ^ (1 / holding_years) − 1
```
- first_buy_date 为空时无法计算 → 返回 None
- cost_price 为 0 时无法计算 → 返回 None

### 3.3 交易记录页（`/transactions`）✅ 已实现

**描述：** 记录每笔买入/卖出操作，作为持仓变动的辅助记录。

**功能点：**
- ✅ 查看交易记录列表（按日期倒序）
- ✅ 新增交易记录（日期、品种、方向、数量、单价、金额、备注）
- ✅ 编辑/删除已有交易记录
- ✅ 支持按品种筛选
- 📋 前端新增/编辑/删除 UI（后端 API 已就绪）
- ~~手续费字段~~——未来优化项，当前不实现

### 3.4 行情查询页（`/quotes`）✅ 已实现

**描述：** 辅助工具，输入标的代码查询实时价格。

**功能点：**
- ✅ 输入框 + 市场/类型下拉选择（A股/A股基金/美股/美股ETF/加密货币）
- ✅ 自动识别代码类型（6位数字→A股，字母→美股，已知符号→加密货币）
- ✅ 查询后展示：名称、最新价、涨跌额+涨跌幅、货币、数据来源、更新时间
- ✅ 数据直接来自行情 API，查询结果不持久化

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
| A 股 | 腾讯财经 HTTP API | httpx 异步请求（默认） |
| 美股 | 腾讯财经 HTTP API | httpx 异步请求（默认，速度最快） |
| 美股 | 新浪财经 + Playwright | 浏览器自动化（备选，获取英文名时使用） |
| 加密货币 | CoinGlass API | httpx 异步请求 |
| 基金 | 天天基金 pingzhongdata / akshare（备选） | httpx 异步请求 |

> 美股数据源对比：腾讯源（HTTP API，~8 股/秒）显著快于新浪源（Playwright，~1 股/秒），默认使用腾讯源。新浪源仅作为备选或获取英文名时使用。

| 数据 | 数据源 | 方式 |
|------|--------|------|
| 汇率 | GitHub raw（ExchangeRates） | httpx 异步，USD 为基准，每小时更新 |

> 汇率四级兜底：内存新鲜值（1h TTL）→ 内存过期旧值 → 运行时缓存 `data/exchange_rates_cache.json` → 种子文件 `data/dbjson/exchange_rates_fallback.json`（提交进仓库）。详见 [architecture.md §5.7](architecture.md)。

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
| HTTP 客户端 | Axios（前端）/ httpx（后端） |
| 状态管理 | Zustand（待用） + TanStack Query |
| 美股爬取 | Playwright (async API) |
