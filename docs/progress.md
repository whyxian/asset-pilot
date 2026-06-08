# AssetPilot 开发进度

> 最后更新：2026-06-07
> 记录所有模块的完成状态、任务拆分和开发规划

---

## 一、已完成 ✅

### 后端基础设施

| 模块 | 文件 | 说明 |
|------|------|------|
| 数据库引擎 | `backend/app/core/database.py` | SQLAlchemy async + init_db，SQLite |
| Pydantic 模型 | `backend/app/models/asset_quote.py` | AssetQuote 统一行情模型 |
| ORM 模型 | `backend/app/models/asset_quote_orm.py` | AssetQuoteRecord，含审计字段 |

### 行情获取（4 个市场，6 个数据源）

| 市场 | 数据源 | Repo 方法 | 说明 |
|------|--------|-----------|------|
| A 股 | 腾讯财经 | `_fetch_from_tencent()` | httpx 异步 |
| A 股 | 东方财富（备选） | `_fetch_from_east_money()` | 待实现 |
| 美股 | 新浪 + Playwright | `_fetch_from_sina()` | 浏览器自动化 |
| 加密货币 | CoinGlass | `_fetch_from_coinglass()` | httpx 异步 |
| 基金 | 天天基金 pingzhongdata | `_fetch_from_pingzhong()` | httpx 异步，默认源 |
| 基金 | akshare | `_fetch_from_akshare()` | 备选源 |

### 行情 API

| 端点 | 文件 | 说明 |
|------|------|------|
| `GET /api/v1/stock/quotes/{market}` | `asset_quote_api.py` | A 股/美股 |
| `GET /api/v1/crypto/quotes` | `asset_quote_api.py` | 加密货币 |
| `GET /api/v1/fund/quotes` | `asset_quote_api.py` | 基金净值 |

### 前端框架

| 模块 | 说明 |
|------|------|
| Vite + React + TS | 项目初始化 |
| Tailwind CSS v4 + shadcn/ui | 样式 + 组件库 |
| lucide-react + recharts | 图标 + 图表 |
| react-router-dom | 4 个路由 |
| 侧边栏布局 | 概览/持仓/交易/行情 导航 |
| JSON 数据文件 | `src/data/overview.json`、`holdings.json`、`transactions.json` |
| 文档对齐 | requirements.md v2.0 + architecture.md v2.1 | 按前端页面重写需求，更新架构文档与实际一致 |

---

## 二、开发路线图 🗺️

依赖关系：Phase 1 → Phase 2 → Phase 3 → (Phase 4) → (Phase 5)

```
Phase 1 (P0) ──→ Phase 1b (P0) ──→ Phase 2 (P0) ──→ Phase 3 (P0)
   持仓 ORM+CRUD    品种数据填充      持仓计算服务      概览汇总 API
       │
       └──→ Phase 4 (P1) ──→ Phase 5 (P2)
              交易记录 CRUD      净值快照
```

---

## 三、Phase 1：持仓 ORM + CRUD（P0）

### 子任务

| # | 任务 | 涉及文件 | 说明 |
|---|------|---------|------|
| 1.1 | ORM 模型 | `backend/app/models/asset_holding_orm.py` | 建表 `asset_holdings`（ticker, name, market, asset_class, currency, quantity, cost_price, total_invested, first_buy_date） |
| 1.2 | init_db 注册 | `backend/app/core/database.py` | 新增 ORM 模型导入 |
| 1.3 | Repository | `backend/app/repositories/asset_holding_repository.py` | CRUD 方法（create / get / update / delete / list） |
| 1.4 | Service | `backend/app/services/asset_holding_service.py` | 调用 repository |
| 1.5 | API 路由 | `backend/app/api/asset_quote_api.py` | 追加 `POST/GET/PUT/DELETE /api/v1/holdings` |

### 验证

```bash
# 启动服务，验证表已创建
sqlite3 data/database/assetpilot.db ".tables"  # 应有 asset_holdings
# 测试新增持仓
curl -X POST http://localhost:8000/api/v1/holdings \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"600519","name":"贵州茅台","market":"A","asset_class":"STOCK","currency":"CNY","quantity":100,"cost_price":1650,"total_invested":165000,"first_buy_date":"2025-01-15"}'
# 测试查询持仓
curl http://localhost:8000/api/v1/holdings
```

---

## 四、Phase 1a：品种验证（P0 ✅）

**描述：** 建 asset_varieties 表，创建持仓时校验品种存在。已全部完成。

| 文件 | 说明 |
|------|------|
| `backend/app/models/asset_variety_orm.py` | ORM 模型 |
| `backend/app/models/asset_variety.py` | Pydantic 模型 |
| `backend/app/repositories/asset_variety_repository.py` | CRUD + 软删除 |
| `backend/app/services/asset_variety_service.py` | 业务逻辑 |
| `backend/app/api/asset_variety_api.py` | `GET/POST/DELETE /api/v1/varieties` |
| `backend/app/services/asset_holding_service.py` | 创建持仓时校验 ticker 是否已注册 |
| `docs/database.md` | 更新说明，移除"未使用"标注 |

---

## 五、Phase 1b：品种数据填充（P0）

**描述：** 为 asset_varieties 填充真实数据，让用户不用手动一个个添加品种。

### 子任务

| # | 任务 | 说明 | 优先级 |
|---|------|------|--------|
| 1b.1 | A 股批量导入脚本 | 用 akshare 获取 A 股列表（~5000 只），写入 asset_varieties | P0 |
| 1b.2 | 基金批量导入脚本 | 用 akshare 获取基金列表（~10000 只），写入 asset_varieties | P0 |
| 1b.3 | 美股 + 加密货币种子数据 | 手动维护一份常用代码 JSON，启动时自动导入 | P0 |
| 1b.4 | 前端品种搜索组件 | 添加持仓时，搜索框支持输入 ticker/名称 自动补全 | P1 |
| 1b.5 | 查询时自动注册 | 创建持仓时品种不存在 → 调用行情验证 → 有效则自动注册（替代报错） | 后续优化 |
| 1b.6 | 定时任务更新品种 | 每周自动检查是否有新品种上市，更新 asset_varieties | P2 |
| 1b.7 | 前端品种管理页 | 列表页展示已注册品种，支持搜索，不可删除 | P2 |

### 批量导入脚本示例

```python
# A 股：用 akshare 拉取全部代码
import akshare as ak
df = ak.stock_zh_a_spot_em()
# → ticker, name → 批量写入 asset_varieties

# 基金：用 akshare 拉取基金列表
df = ak.fund_name_em()
# → ticker, name → 批量写入 asset_varieties
```

### 验证

```bash
# 运行批量导入脚本后
curl http://localhost:8100/api/v1/varieties
# 应返回数千条 A 股 + 基金数据
```

---

## 六、Phase 2：持仓计算服务（P0）

### 子任务

| # | 任务 | 涉及文件 | 说明 |
|---|------|---------|------|
| 2.1 | 持仓计算 | `asset_holding_service.py` | 读取持仓 → 获取行情 → 计算市值/盈亏/年化 |
| 2.2 | 年化回报率 | `asset_holding_service.py` | (现价/成本价)^(1/持有年数)-1 |
| 2.3 | 计算 API | `asset_quote_api.py` | `GET /api/v1/holdings/with-quotes` 返回带实时行的持仓 |

### 计算公式

```
市值 = quantity × current_price
盈亏额 = market_value - total_invested
盈亏% = (market_value / total_invested - 1) × 100
持有年数 = (today - first_buy_date).days / 365
年化回报率 = (current_price / cost_price) ^ (1 / holding_years) - 1
```

### 验证

```bash
curl http://localhost:8000/api/v1/holdings/with-quotes
# 应返回持仓数据 + 实时价 + 市值 + 盈亏 + 年化
```

---

## 七、Phase 3：概览汇总 API（P0）

### 子任务

| # | 任务 | 涉及文件 | 说明 |
|---|------|---------|------|
| 3.1 | 概览服务 | `asset_holding_service.py` | 聚合持仓：总市值/成本/盈亏/年化 |
| 3.2 | 资产配比 | `asset_holding_service.py` | 按 market 分组统计市值占比 |
| 3.3 | 概览 API | `asset_quote_api.py` | `GET /api/v1/overview` |

### 验证

```bash
curl http://localhost:8000/api/v1/overview
# 应返回 { total_value, total_cost, total_pnl, annualized_return, allocation[] }
```

---

## 八、Phase 4：交易记录 CRUD（P1）

### 子任务

| # | 任务 | 涉及文件 | 说明 |
|---|------|---------|------|
| 4.1 | ORM 模型 | `backend/app/models/transaction_orm.py` | 建表 `transactions` |
| 4.2 | Repository | `backend/app/repositories/transaction_repository.py` | CRUD 方法 |
| 4.3 | Service | `backend/app/services/transaction_service.py` | 业务逻辑 |
| 4.4 | API | `backend/app/api/transaction_api.py` | `GET/POST/PUT/DELETE /api/v1/transactions` |

---

## 九、Phase 5：净值快照（P2）

### 子任务

| # | 任务 | 涉及文件 | 说明 |
|---|------|---------|------|
| 5.1 | ORM 模型 | `backend/app/models/networth_snapshot_orm.py` | 建表 `networth_snapshots` |
| 5.2 | Repository + Service | 对应文件 | 快照生成与查询 |
| 5.3 | API | | `POST /api/v1/networth/snapshot` 生成当日快照 |
| 5.4 | API | | `GET /api/v1/networth/history` 查询历史净值 |

---

## 十、后续规划

| 项目 | 说明 |
|------|------|
| 前端对接后端 | Phase 1-3 完成后，前端从 JSON 切换到后端 API |
| 定投计划 | 按周期自动生成交易记录并更新持仓 |
| 定时任务 | 每日自动抓取行情 + 生成净值快照 |

---

## 十一、开发中 ⏳

_当前正在进行的任务_

| 阶段 | 任务 | 开始时间 |
|------|------|---------|
| Phase 1 | 持仓 ORM + CRUD | 2026-06-07 ✅ |
| Phase 1a | 品种验证（asset_varieties 表+API+持仓校验） | 2026-06-07 ✅ |
| Phase 1b | 品种数据填充（批量导入脚本+前端搜索+自动注册） | 2026-06-07 ⏳ |
| 架构改进 | 统一异常处理 + 统一返回 + CORS + 请求日志 | 2026-06-07 ✅ |
| Phase 2 | 持仓计算服务 | 待开始 |
| Phase 3 | 概览汇总 API | 待开始 |
