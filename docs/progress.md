# AssetPilot 开发进度

> 最后更新：2026-06-13
> 记录所有模块的完成状态、任务拆分和开发规划

---

## 一、开发路线图

```
Phase 1 ──→ Phase 1a ──→ Phase 1b ──→ Phase 2 ──→ Phase 4 ──→ 持仓 UI ──→ Phase 5 ──→ 交易→持仓自动反推
 持仓CRUD     品种验证      数据填充      持仓计算      前端对接     增删改      交易CRUD       建仓基线 + 全量重算
```

| 阶段 | 内容 | 完成时间 | 状态 |
|------|------|---------|------|
| Phase 1 | 持仓 ORM + CRUD | 2026-06-07 | ✅ |
| Phase 1a | 品种验证（asset_varieties 表+API） | 2026-06-07 | ✅ |
| Phase 1b | 品种数据填充（45884 条，四市场全覆盖） | 2026-06-10 | ✅ |
| Phase 2 | 持仓计算服务（with-quotes API） | 2026-06-07 | ✅ |
| Phase 4 | 前后端对接（4 页切到真实 API） | 2026-06-10 | ✅ |
| 持仓 UI | 增删改对话框 + 品种搜索自动填充 | 2026-06-11 | ✅ |
| Phase 5 | 交易记录 CRUD（后端+前端） | 2026-06-10 | ✅ |
| 概览 API | GET /api/v1/overview（后端聚合 + 汇率换算） | 2026-06-11 | ✅ |
| 汇率工具 | exchange_rate.py（GitHub 源 + 1h 缓存） | 2026-06-11 | ✅ |
| 精度修复 | 前端数字格式化 T0 级重写 | 2026-06-11 | ✅ |
| 数据自动刷新 | 概览/持仓页 60s 轮询 + 持仓变更联动失效概览缓存 | 2026-06-13 | ✅ |
| 交易→持仓自动反推 | 建仓基线 + 全量重算（加权平均/卖超拒绝/事务原子）+ 交易页 CRUD UI | 2026-06-13 | ✅ |
| Phase 6 | 净值快照 | — | 📋 下一步 |
| 图表 | Recharts 折线图/饼图 | — | 📋 规划中 |

---

## 二、数据库

| 表 | 行数 | 说明 |
|----|------|------|
| `asset_varieties` | 45,884 | 品种目录 |
| `asset_holdings` | ~4 | 当前持仓 |
| `asset_quote` | ~60 | 行情记录 |
| `transactions` | 0 | 交易记录（表已建，待录入） |

---

## 三、后端 API 端点

### 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/overview` | 概览统计（CNY 统一换算） |

### 行情

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/stock/quotes/{CN,US}?codes=` | A 股/美股实时行情 |
| `GET` | `/api/v1/crypto/quotes?coins=` | 加密货币行情 |
| `GET` | `/api/v1/fund/quotes/{CN,US}?codes=` | 基金/ETF 净值 |
| `GET` | `/api/v1/varieties` | 品种目录 |
| `GET` | `/api/v1/varieties/search?q=&limit=` | 品种搜索（ticker/名称模糊匹配） |
| `POST` | `/api/v1/varieties` | 添加品种 |
| `DELETE` | `/api/v1/varieties/{ticker}` | 删除品种（软删除） |

### 持仓

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/holdings` | 持仓列表 |
| `GET` | `/api/v1/holdings/with-quotes` | 持仓 + 实时行情 + 市值/盈亏/年化 |
| `GET` | `/api/v1/holdings/{ticker}` | 单个持仓 |
| `POST` | `/api/v1/holdings` | 新增持仓（名称空时自动补填） |
| `PUT` | `/api/v1/holdings/{ticker}` | 更新持仓 |
| `DELETE` | `/api/v1/holdings/{ticker}` | 删除持仓 |

### 交易

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/transactions[?ticker=][&limit=]` | 交易列表 |
| `GET` | `/api/v1/transactions/{id}` | 单条交易 |
| `POST` | `/api/v1/transactions` | 新增交易 |
| `PUT` | `/api/v1/transactions/{id}` | 更新交易 |
| `DELETE` | `/api/v1/transactions/{id}` | 删除交易 |

---

## 四、项目文件

→ 详见 [architecture.md](architecture.md)

---

## 五、已知问题 / 技术债

| # | 说明 | 严重度 | 状态 |
|----|------|--------|------|
| 1 | `asset_quote` 表缺少 UNIQUE(ticker, timestamp) 约束 | 中 | ✅ 已修（2026-06-13）<br>ORM 已加约束 + 提供迁移脚本 `backend/script/migrate_asset_quote_unique.py` |
| 2 | `SinaDataSource.close()` 缺少 try/finally | 低 | ✅ 已修（2026-06-13） |
| 3 | ORM `currency` 字段缺默认值 | 低 | ✅ 已修（2026-06-13）<br>`AssetVariety` ORM/Pydantic 均补 `USD` 默认值 |
| 4 | 前端 chunks > 500KB，可按页面 code-split | 低 | ✅ 已修（2026-06-13）<br>路由改 `React.lazy`，最大 chunk 从 >500KB 降至 245KB |

---

## 六、后续规划

| 优先级 | 项目 | 说明 |
|--------|------|------|
| P1 | 净值快照 | `asset_snapshots` + `networth_snapshots` 表 + 快照 API |
| P2 | 前端图表 | 净值走势（Recharts 折线图）+ 资产配比（饼图） |
| P3 | 定时任务 | 每日自动抓取行情 + 汇率 + 快照 |
| P4 | 定投计划 | 周期自动生成交易记录并更新持仓 |
