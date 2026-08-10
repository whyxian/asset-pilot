# AssetPilot V2 架构设计

> 版本：v2.9
> 最后更新：2026-08-04（新增现金账户机制 §5.14 + 统一分页 §5.15 + 目录结构补全快照/归档/现金模块）

---

## 1. 设计目标

- 前后端分离，职责清晰
- 持仓为主、交易为辅：持仓是直接维护的事实源，交易记录只作为辅助记录
- 价格数据持久化，支持历史净值曲线
- 可扩展的 API 架构，便于未来接入更多数据源或客户端

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | React 19 + TypeScript + Vite | SPA 框架（已初始化） |
| 样式 | Tailwind CSS v4 + shadcn/ui | 组件库（button, card, table, dialog, form 等） |
| 图表 | Recharts | 性能曲线与资产配比 |
| 状态管理 | Zustand | 布局偏好等客户端状态 |
| 服务端缓存 | TanStack Query | API 数据缓存 |
| 后端 | FastAPI (Python 3.11+) | 异步 API 框架 |
| 定时任务 | APScheduler (AsyncIOScheduler) | 行情/汇率后台定时预热 |
| ORM | SQLAlchemy 2.0 (async) | 数据库抽象层 |
| 数据库 | SQLite (aiosqlite) | 单用户无需部署服务 |
| 行情源 | 腾讯财经 / 新浪+Playwright / CoinGlass / 天天基金 | 四市场行情 |
| 收益率 | 简单年化回报率 | (现价/成本价)^(1/持有年数) - 1 |

## 3. 目录结构

```
AssetPilot/
├── backend/            # 后端服务（FastAPI + SQLite）
│   ├── app/            #   应用代码
│   ├── script/         #   数据导入/处理脚本
│   ├── test/           #   测试
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/           # 前端 SPA（规划中，React + Vite）
├── data/               # 运行时数据（SQLite 数据库文件）
├── docs/               # 文档
│   ├── architecture.md
│   ├── requirements.md
│   ├── database.md
│   └── progress.md
├── .gitignore
├── CLAUDE.md
└── README.md
```

### 3.2 后端

```
backend/
├── pyproject.toml
├── requirements.txt
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── core/
│   │   ├── database.py            # SQLAlchemy 引擎 + init_db
│   │   ├── data_sources.py        # 5 个数据源类（腾讯/新浪/CoinGlass/天天基金/akshare）
│   │   ├── exceptions.py          # BusinessError
│   │   ├── logger.py              # 统一日志
│   │   ├── response.py            # ApiResponse 统一返回格式
│   │   └── scheduler_config.py    # 统一配置：调度间隔/缓存TTL/网络超时（SchedulerConfig）
│   ├── api/                       # HTTP 路由层
│   │   ├── asset_quote_api.py     # 行情接口（A股/美股/加密货币/基金）
│   │   ├── asset_holding_api.py   # 持仓 CRUD
│   │   ├── asset_variety_api.py   # 品种目录 CRUD
│   │   ├── overview_api.py        # 概览统计
│   │   ├── transaction_api.py     # 交易记录 CRUD
│   │   ├── snapshot_api.py        # 净值快照（组合级 + 品种级）
│   │   ├── closed_holding_api.py  # 历史持仓归档
│   │   └── cash_flow_api.py       # 资金流水（入金/出金/余额/流水）
│   ├── models/                    # 数据模型
│   │   ├── asset_quote.py         # AssetQuote (Pydantic)
│   │   ├── asset_holding.py       # AssetHolding / HoldingWithQuote (Pydantic)
│   │   ├── asset_variety.py       # AssetVariety (Pydantic)
│   │   ├── transaction.py         # Transaction / Create / Update (Pydantic)
│   │   ├── overview.py            # OverviewStats / AllocationItem (Pydantic)
│   │   ├── cash_flow.py           # CashFlow / CashBalance / CashDeposit(Create) (Pydantic)
│   │   ├── common.py              # PaginatedResponse[T] 统一分页模型（跨模块共享）
│   │   └── orm/                   # SQLAlchemy ORM 模型
│   │       ├── asset_quote_orm.py
│   │       ├── asset_holding_orm.py
│   │       ├── asset_variety_orm.py
│   │       ├── transaction_orm.py
│   │       ├── asset_snapshot_orm.py
│   │       ├── networth_snapshot_orm.py
│   │       ├── closed_holding_orm.py
│   │       └── cash_flow_orm.py   # CashFlowRecord（含 transaction_id FK）
│   ├── repositories/              # 数据访问层
│   │   ├── asset_quote_repository.py  # 行情 Repo（调用 DataSource）
│   │   ├── asset_holding_repository.py# 持仓 CRUD
│   │   ├── asset_variety_repository.py# 品种目录 CRUD
│   │   ├── transaction_repository.py  # 交易记录 CRUD（分页）
│   │   ├── snapshot_repository.py     # 净值快照读写
│   │   ├── closed_holding_repository.py# 历史持仓归档（含删除时连带删 cash_flows）
│   │   └── cash_flow_repository.py    # 资金流水 CRUD + 余额聚合
│   └── services/                  # 业务逻辑层
│       ├── asset_quote_service.py # 行情业务逻辑（QuoteCache 缓存 + force_refresh 绕过 + DB 历史降级）
│       ├── asset_holding_service.py# 持仓业务逻辑（含计算 + 建仓现金联动）
│       ├── asset_variety_service.py# 品种目录业务逻辑
│       ├── overview_service.py    # 概览统计（行情并发拉取 + 12s 超时熔断 + 汇率换算聚合）
│       ├── transaction_service.py # 交易记录业务逻辑（买卖自动联动现金流水）
│       ├── snapshot_service.py    # 净值快照（双表写 + 历史 FX 冻结）
│       ├── closed_holding_service.py# 历史持仓归档
│       └── cash_flow_service.py   # 资金流水（入金/出金/余额按显示币种换算）
├── scheduler/                # 后台定时任务（APScheduler）
│   └── quote_scheduler.py     # 行情30s + 汇率55min 定时预热，写全局 QuoteCache
├── utils/                     # 工具模块
│   ├── exchange_rate.py       # 汇率获取（GitHub 源 + 五级兜底 + 单飞）
│   ├── quote_cache.py         # 行情内存缓存（进程级单例，单ticker+部分命中）
│   └── trading_hours.py       # 交易时段判定（A股/美股/加密/基金）
├── script/                   # 数据导入/处理脚本
│   ├── json_tools.py          # JSON 工具（拆分/合并/重命名 key / 区分股基）
│   ├── seed_varieties.py      # 导入 JSON 品种数据到 DB
│   ├── fetch_us_names.py      # 批量获取美股英文名
│   ├── fetch_cn_fund.py       # 天天基金数据采集
│   └── fetch_us_stocks.py     # 东方财富美股数据采集
├── test/                      # 单元测试（pytest + pytest-asyncio，内存 SQLite）
│   ├── conftest.py            # 共享 fixture（engine/Session/seed_*/approx）
│   ├── test_transaction_recompute.py    # 重算 + 归档算法
│   ├── test_asset_holding_service.py    # 持仓 CRUD + 三元组行情
│   ├── test_transaction_service.py      # 交易 CRUD + 校验链 + 事务回滚
│   ├── test_exchange_rate.py            # 汇率缓存 + 四级兜底 + 转换
│   ├── test_overview_service.py         # 概览聚合 + 年化 + 行情并发熔断
│   ├── test_asset_quote_service.py      # 行情缓存 + 名称补全 + 路由
│   ├── test_data_sources.py             # 数据源解析（mock httpx）
│   ├── test_asset_variety_repository.py # 品种搜索相关性排序
│   ├── test_asset_quote_repository.py   # 行情去重 + 缓存查询
│   ├── test_quote_cache.py              # 缓存命中/过期不丢/部分命中
│   ├── test_trading_hours.py            # 交易时段判定
│   └── test_snapshot_service.py         # 净值快照双表写 + FX 冻结
└── Dockerfile
```

### 3.3 前端

SPA 单页应用 + 侧边栏布局。已对接后端 API，使用 TanStack Query + Axios。

```
frontend/
├── src/
│   ├── api/                       # API 客户端
│   │   ├── client.ts              # Axios 实例 + 响应拦截器
│   │   ├── endpoints.ts           # 所有端点函数
│   │   └── types.ts               # ApiResponse / ApiError
│   ├── hooks/                     # 数据 hooks
│   │   ├── useHoldings.ts         # 持仓查询（共享缓存）
│   │   ├── useHoldingMutations.ts # 持仓增删改
│   │   ├── useQuote.ts            # 行情查询
│   │   ├── useTransactions.ts     # 交易查询
│   │   ├── useClosedHoldings.ts   # 历史持仓查询
│   │   └── useCashFlows.ts        # 现金流水 + 余额查询
│   ├── lib/
│   │   └── settings.ts            # 显示币种等偏好设置（localStorage）
│   ├── types/
│   │   └── index.ts               # TS 类型定义
│   ├── components/
│   │   ├── layout/                # 侧边栏布局
│   │   └── ui/                    # shadcn/ui 组件（badge/button/card/dialog/input/pagination/select/sheet/skeleton/table）
│   ├── features/                  # 按功能域组织
│   │   ├── overview/              # 概览：统计卡 + 净值走势图 + 资产配比 + 手动刷新按钮
│   │   ├── holdings/              # 持仓表格 + 新增/编辑/删除 + 手动刷新按钮
│   │   ├── transactions/          # 交易记录列表（分页）
│   │   ├── cash/                  # 现金页：余额卡片 + 入金/出金 + 流水列表（分页）
│   │   ├── history/               # 历史持仓（归档持仓 + 归档交易，分页）
│   │   └── quotes/                # 行情查询（输入+市场选择+结果卡片）
│   ├── routes/
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── vite.config.ts                # 含 /api 代理到 localhost:8000
├── tsconfig.json
└── package.json
```

页面视图：

| 视图 | 路由 | 内容 | 数据来源 |
|------|------|------|---------|
| 概览 | `/` | 总市值/成本/盈亏统计卡 + 净值走势 + 资产配比条 | `GET /api/v1/overview` |
| 持仓 | `/holdings` | 品种表格 + 年化回报 + 增删改操作 | `GET /api/v1/holdings/with-quotes` |
| 交易 | `/transactions` | 交易记录列表（按日期倒序，分页） | `GET /api/v1/transactions` |
| 行情 | `/quotes` | 输入代码 + 市场选择 → 查询实时行情 | `GET /api/v1/{stock,crypto,fund}/quotes` |
| 现金 | `/cash` | 余额卡片 + 入金/出金 + 流水列表（分页） | `GET /api/v1/cash/balances`、`/flows` |
| 历史持仓 | `/holdings/history` | 归档持仓列表（分页） | `GET /api/v1/closed-holdings` |
| 历史交易 | `/transactions/history` | 归档交易列表（分页） | `GET /api/v1/closed-transactions` |

## 4. 分层架构

```
┌──────────────────────────────────────────┐
│     middleware（全局中间件）                │  CORS / 请求日志 / 全局异常处理
├──────────────────────────────────────────┤
│              api（HTTP 路由）              │  参数校验，调用 service，返回 ApiResponse
├──────────────────────────────────────────┤
│           services（业务逻辑）             │  编排逻辑，抛出 BusinessError
├──────────────────────────────────────────┤
│        repositories（数据访问层）           │  调用 DataSource 或操作 DB
├──────────────────────────────────────────┤
│         data_sources（数据源层）            │  纯获取逻辑，通过 supports() 路由
├──────────────────────────────────────────┤
│            models（数据模型）              │  Pydantic / SQLAlchemy
└──────────────────────────────────────────┘
```

## 5. 设计要点

### 5.1 行情统一模型

`AssetQuote` 归一化四个市场（A股、美股、加密货币、基金）的行情输出，下游（service / api）不关心数据来源。

### 5.2 异步并发

- A 股 / 加密货币 / 基金 / 美股（腾讯源）：httpx async + `asyncio.gather` 并发
- 美股（新浪源）：Playwright async API，浏览器单例复用

### 5.3 多数据源切换

每个 Repository 支持通过 `source` 参数切换数据源：

```python
quotes = await repo.fetch_realtime_quote(["166002"])               # 默认源
quotes = await repo.fetch_realtime_quote(["166002"], source="akshare")  # ak share
```

当前实现的数据源（按 `supports(asset_class, market)` 路由）：

| DataSource | name | 覆盖范围 |
|-----------|------|---------|
| `TencentDataSource` | `tencent` | STOCK+CN / STOCK+US / FUND+US |
| `SinaDataSource` | `sina` | STOCK + US（Playwright 备选） |
| `CoinGlassDataSource` | `coinglass` | CRYPTO |
| `EastMoneyFundDataSource` | `pingzhong` | FUND（默认） |
| `AkshareFundDataSource` | `akshare` | FUND（备选） |

### 5.4 统一异常处理与返回格式

所有 API 返回统一格式 `{ code, message, data }`：

```json
// 成功
{ "code": 0, "message": "ok", "data": [...] }

// 业务校验失败
{ "code": 40001, "message": "未识别的品种代码", "data": null }

// 行情不可用（数据源查无此代码）
{ "code": 40002, "message": "未找到 999999 的行情，请检查代码或市场类型", "data": null }

// 未找到
{ "code": 40401, "message": "持仓不存在", "data": null }
```

**错误码统一在 `core/error_codes.py` 管理**（常量 `CODE_VALIDATION` / `CODE_QUOTE_UNAVAILABLE` / `CODE_NOT_FOUND` 等），
禁止散落硬编码。服务层通过抛出 `BusinessError(code, message)` 触发业务错误，全局异常处理器统一捕获。
框架层：404（路由不存在）、422（参数校验，FastAPI 原生 `{"detail": ...}` 格式）、500（未捕获异常）。

| 层 | 策略 |
|----|------|
| middleware | 全局 CORS / 请求日志 / BusinessError & HTTPException 统一捕获 |
| services | 抛出 `BusinessError`，不处理 HTTP 细节 |
| repositories | 返回 `None` 表示未找到，向上抛异常 |
| api | 调用 service，用 `success(data)` 包裹返回，不写 try/except |

### 5.5 美股品种分类（STOCK vs FUND）

美股来源（东方财富 m:105/m:106/m:107）混合了股票和 ETF/基金，入库前需区分：

- **分类依据**：按名称关键词匹配（`FUND_KEYWORDS`），仅使用不会误伤公司名的基金标识词
- **分类结果**：5542 基金/ETF（`asset_class` → `FUND`）+ 7843 纯股票
- **工具函数**：`json_tools.split_stock_vs_fund()` 可复用

### 5.6 JSON → DB 导入工具

`seed_varieties.py` 负责将清洗后的 JSON 数据批量导入 `asset_varieties` 表：

- 按 `(asset_class, market, ticker)` 复合键去重，已有记录自动跳过
- 每 1000 条输出一次进度
- 支持分文件逐个导入

### 5.7 汇率五级兜底 + 单飞

`utils/exchange_rate.py` 以 USD 为枢轴做币种换算，汇率来源单一（GitHub raw），故采用五级兜底 + 单飞保证可用性：

```
内存新鲜值（1h TTL 内）→ 网络拉取 → 内存过期旧值 → 磁盘旧值（运行时缓存→种子文件）→ 硬编码常量
```

- 磁盘兜底两层（`_load_persisted` 优先读前者）：`data/exchange_rates_cache.json`（运行时，gitignore）→ `data/dbjson/exchange_rates_fallback.json`（种子，提交进仓库）
- 硬编码常量 `_HARDCODED_RATES`（嵌入 exchange_rate.py）：种子文件也被删时的终极兜底，`fetch_rates` 永不返回 None
- **单飞**（`_inflight` task）：N 个并发请求同时触发网络拉取时只发 1 个请求，其余复用结果
- **日期+新鲜度透传**：`fetch_rates` 返回 `RatesSnapshot{rates, source_date, is_stale}`，概览页脚展示汇率日期，兜底时变橙色警告

### 5.8 概览行情并发拉取与熔断

`OverviewService.get_overview` 拉行情时的稳定性设计：

- **组间并发**：按 `(asset_class, market)` 分组后用 `asyncio.wait` 并发拉取，总耗时 ≈ 最慢一组而非串行累加
- **整体超时熔断**（`SchedulerConfig.QUOTE_FETCH_TIMEOUT = 12s`，比前端 axios 15s 略早）：超时组取消，单组异常吞掉
- **汇率一次取回**：循环外 `fetch_rates()` 取一次，循环内用同步 `convert_with_rates`，消除 2N 次冗余 await

### 5.9 行情降级兜底（QuoteStatus 三态）

`fetch_quote_map_concurrent` 拉行情时部分 ticker 失败的处理：反推失败 codes → 查 DB 最新历史兜底，返回带状态的行情：

- `REALTIME`：实时行情（数据源刚拉的）
- `HISTORICAL`：DB 历史兜底（实时失败，回查 `get_latest_quotes` 不限时间最新一条）
- `UNAVAILABLE`：连历史都没有（建仓后从未成功落库的极端情况）

建仓时强制拉行情落库（`create_holding`），保证 DB 永远有该 ticker 的历史兜底。前端持仓页现价/市值按状态标记：HISTORICAL 追加"历史"小字，UNAVAILABLE 显示"—"。

### 5.10 行情缓存层（QuoteCache）

`utils/quote_cache.py` 进程级单例，单 ticker 粒度 + 部分命中：

- 按 `(market, ticker)` 单条缓存，跨用户/跨页面复用（A、B 用户都查 600519 共享）
- 部分命中：codes 里命中若干只、缺若干只时只拉缺失的
- **过期不丢弃**：TTL 过期的数据仍返回（进 hit 标记 stale），用户请求永远不触网——避免调度器故障时 N 个并发请求轰数据源

### 5.11 后台定时预热（APScheduler）

`scheduler/quote_scheduler.py` 后台定时拉数据写缓存，**用户请求永远只读缓存**，彻底解耦用户请求与数据源：

- 行情 30s + 汇率 55min，启动时预热（`asyncio.gather` 并发拉一次）
- 行情按市场+交易时段判断是否真刷新：交易时段必刷，非交易 30min 一次，基金 15min 一次
- 调度器失败时查 DB 历史兜底写缓存，保证缓存永不过期
- 配置统一在 `SchedulerConfig`（见 5.12）

### 5.12 统一配置（SchedulerConfig）

`core/scheduler_config.py` 集中管理调度间隔/缓存TTL/网络超时，消除散落硬编码：

- 调度器间隔：行情 30s、汇率 55min
- 各市场刷新间隔：基金 15min、非交易 30min
- 缓存兜底 TTL：行情 5min、汇率 1h
- 网络超时：汇率 5s、行情熔断 12s、腾讯 10s、基金 15s、CoinGlass 10s、Playwright 20s/10s

铁律：任何后端外部请求超时 ≤ 前端 axios 15s。改一处全局生效。

### 5.13 手动强制刷新

持仓页/概览页刷新按钮通过 `force_refresh=true` 强制拉最新行情：

- 跳过缓存读、走网络、**也写缓存**（保持手动刷新后读取一致，不再出现"刷新看到价格B、切回看到价格A"）
- 前端用 `useMutation` + `setQueryData` 一次性触发，60s 轮询仍走正常缓存
- 汇率不 force（1h 才更新，刷新按钮只针对行情）

API 端点：`GET /api/v1/holdings/with-quotes?force_refresh=true`、`GET /api/v1/overview?currency=CNY&force_refresh=true`

### 5.14 现金账户机制（cash_flows）

`cash_flows` 表独立于 transactions，记录所有资金进出（`deposit`/`withdraw`/`buy`/`sell`，正=入账负=出账），是现金余额的唯一事实源：

- **买卖自动联动**：`TransactionService` 写交易时在同一事务内生成流水——buy 生成扣款流水（校验同币种余额充足），sell 生成入账流水；更新交易同步改流水金额，删除交易回退流水。**现金追踪永远开**，不检查 `cash_account_enabled`
- **建仓联动**：`AssetHoldingService.create_holding` 中 `cash_account_enabled` 只决定资金来源——勾选=从现有现金余额扣款（校验余额不足则拒绝），不勾选=自动先入金等额（notes="建仓 XX 自动入金（历史本金）"）再扣款，代表历史本金注入
- **余额换算**：`CashFlowService.get_balances` 各币种原始余额 + 用 `fetch_rates()`（单飞复用）按显示币种换算总额，与概览页模式一致；响应带 `rate_source_date` / `rate_stale` 供前端展示汇率日期/兜底警告
- **归档联动**：归档时原 transactions 删除，流水 `transaction_id` 成悬空引用（SQLite 不强制 FK）；删除归档持仓时经 `closed_transactions.original_id` 回溯删除关联 buy/sell 流水，自动入金流水（`transaction_id=NULL`）保留
- **出金校验**：`POST /api/v1/cash/withdraw` 在 API 层校验同币种余额充足

### 5.15 统一分页（PaginatedResponse）

所有列表接口统一分页结构（`models/common.py` 的 `PaginatedResponse[T]`，Pydantic Generic）：

```json
{ "data": [...], "total": 125, "page": 3, "page_size": 20 }
```

- 已接入：交易（`/transactions`）、归档持仓（`/closed-holdings`）、归档交易（`/closed-holdings/transactions`）、现金流水（`/cash/flows`）
- 参数：`page`（≥1，默认 1）、`page_size`（1-100，默认 20），仓储层 `limit + offset`
- 前端 `Pagination` 组件（components/ui/pagination.tsx）统一渲染页码器
