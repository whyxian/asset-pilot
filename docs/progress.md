# AssetPilot 开发进度

> 最后更新：2026-06-10
> 记录所有模块的完成状态、任务拆分和开发规划

---

## 一、开发路线图

```
Phase 1 ──→ Phase 1a ──→ Phase 1b ──→ Phase 2 ──→ Phase 4 ──→ 持仓 UI ──→ Phase 5
 持仓CRUD     品种验证      数据填充      持仓计算      前端对接     增删改      交易CRUD
                                                                    ↓
                                                               Bug 修复 ✅
```

| 阶段 | 内容 | 完成时间 | 状态 |
|------|------|---------|------|
| Phase 1 | 持仓 ORM + CRUD | 2026-06-07 | ✅ |
| Phase 1a | 品种验证（asset_varieties 表+API） | 2026-06-07 | ✅ |
| Phase 1b | 品种数据填充（45884 条，四市场全覆盖） | 2026-06-10 | ✅ |
| Phase 2 | 持仓计算服务（with-quotes API） | 2026-06-07 | ✅ |
| Phase 4 | 前后端对接（4 页切到真实 API） | 2026-06-10 | ✅ |
| 持仓 UI | 增删改对话框 + 表单 | 2026-06-10 | ✅ |
| Phase 5 | 交易记录 CRUD（后端+前端） | 2026-06-10 | ✅ |
| Bug 修复 | 前后端 15 项 bug 修复 | 2026-06-10 | ✅ |
| Phase 6 | 净值快照 | — | 📋 下一步 |
| 图表 | 净值走势 + 资产配比饼图（Recharts） | — | 📋 规划中 |

Phase 3（概览汇总 API）已跳过——概览数据由前端从 `holdings/with-quotes` 计算得出。

---

## 二、数据库

### 表一览

| 表 | 行数 | 说明 |
|----|------|------|
| `asset_varieties` | 45,884 | 品种目录（5525 A股 + 7837 美股 + 24931 基金 + 2049 ETF + 5542 美股基金） |
| `asset_holdings` | 3 | 当前持仓 |
| `asset_quote` | 54 | 行情记录 |
| `transactions` | 0 | 交易记录（表已建，待录入） |

---

## 三、后端 API 端点

### 行情

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/stock/quotes/{CN,US}?codes=` | A 股/美股实时行情 |
| `GET` | `/api/v1/crypto/quotes?coins=` | 加密货币行情 |
| `GET` | `/api/v1/fund/quotes/{CN,US}?codes=` | 基金/ETF 净值 |
| `GET` | `/api/v1/varieties` | 品种目录 |
| `POST` | `/api/v1/varieties` | 添加品种 |
| `DELETE` | `/api/v1/varieties/{ticker}` | 删除品种（软删除） |

### 持仓

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/holdings` | 持仓列表（无实时行情） |
| `GET` | `/api/v1/holdings/with-quotes` | 持仓 + 实时行情 + 市值/盈亏/年化 |
| `GET` | `/api/v1/holdings/{ticker}` | 单个持仓 |
| `POST` | `/api/v1/holdings` | 新增持仓 |
| `PUT` | `/api/v1/holdings/{ticker}` | 更新持仓 |
| `DELETE` | `/api/v1/holdings/{ticker}` | 删除持仓 |

### 交易

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/transactions` | 交易列表（支持 `?ticker=` 筛选 + `?limit=`） |
| `GET` | `/api/v1/transactions/{id}` | 单条交易 |
| `POST` | `/api/v1/transactions` | 新增交易（校验品种存在 + quantity×price 和 amount 至少填一组） |
| `PUT` | `/api/v1/transactions/{id}` | 更新交易 |
| `DELETE` | `/api/v1/transactions/{id}` | 删除交易 |

---

## 四、项目文件

→ 详见 [architecture.md](architecture.md) 第 3 节「目录结构」



## 五、已知问题 / 技术债

| # | 说明 | 严重度 | 状态 |
|----|------|--------|------|
| 1 | `asset_quote` 表缺少 UNIQUE(ticker, timestamp) 约束，可能产生重复行情数据 | 中 | 未修 |
| 2 | `SinaDataSource.close()` 缺少 try/finally，`_browser.close()` 异常时 Playwright 泄漏 | 低 | 未修 |
| 3 | ORM `currency` 字段缺默认值，与文档不一致 | 低 | 未修 |
| 4 | 前端 chunks > 500KB，可按页面 code-split | 低 | 未修 |
| 5 | 无品种搜索/自动补全，新增持仓时需手动输入 ticker | 低 | 📋 规划 |

---

## 六、后续规划

| 优先级 | 项目 | 说明 |
|--------|------|------|
| P1 | Phase 6：净值快照 | `asset_snapshots` + `networth_snapshots` 表 + 定时快照 API |
| P2 | 前端图表 | 净值走势用 Recharts 折线图，资产配比用饼图（替代当前进度条） |
| P2 | 品种搜索组件 | 新增持仓时 ticker 自动补全 |
| P3 | 定时任务 | 每日自动抓取行情 + 生成净值快照 |
| P4 | 定投计划 | 按周期自动生成交易记录并更新持仓 |
