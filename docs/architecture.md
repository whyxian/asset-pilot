# AssetPilot V2 架构设计

> 版本：v2.7
> 最后更新：2026-06-19

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
│   │   └── response.py            # ApiResponse 统一返回格式
│   ├── api/                       # HTTP 路由层
│   │   ├── asset_quote_api.py     # 行情接口（A股/美股/加密货币/基金）
│   │   ├── asset_holding_api.py   # 持仓 CRUD
│   │   ├── asset_variety_api.py   # 品种目录 CRUD
│   │   ├── overview_api.py        # 概览统计
│   │   └── transaction_api.py     # 交易记录 CRUD
│   ├── models/                    # 数据模型
│   │   ├── asset_quote.py         # AssetQuote (Pydantic)
│   │   ├── asset_holding.py       # AssetHolding / HoldingWithQuote (Pydantic)
│   │   ├── asset_variety.py       # AssetVariety (Pydantic)
│   │   ├── transaction.py         # Transaction / Create / Update (Pydantic)
│   │   └── orm/                   # SQLAlchemy ORM 模型
│   │       ├── asset_quote_orm.py
│   │       ├── asset_holding_orm.py
│   │       ├── asset_variety_orm.py
│   │       └── transaction_orm.py
│   ├── repositories/              # 数据访问层
│   │   ├── asset_quote_repository.py  # 行情 Repo（调用 DataSource）
│   │   ├── asset_holding_repository.py# 持仓 CRUD
│   │   ├── asset_variety_repository.py# 品种目录 CRUD
│   │   └── transaction_repository.py  # 交易记录 CRUD
│   └── services/                  # 业务逻辑层
│       ├── asset_quote_service.py # 行情业务逻辑（基金 15min 缓存 + force_refresh 绕过）
│       ├── asset_holding_service.py# 持仓业务逻辑（含计算）
│       ├── asset_variety_service.py# 品种目录业务逻辑
│       ├── overview_service.py    # 概览统计（行情并发拉取 + 12s 超时熔断 + 汇率换算聚合）
│       └── transaction_service.py # 交易记录业务逻辑
├── utils/                     # 工具模块
│   └── exchange_rate.py       # 汇率获取（GitHub 源 + 四级兜底：内存1h→内存过期→运行时缓存→种子文件）
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
│   └── test_asset_quote_repository.py   # 行情去重 + 缓存查询
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
│   │   └── useTransactions.ts     # 交易查询
│   ├── types/
│   │   └── index.ts               # TS 类型定义
│   ├── components/
│   │   ├── layout/                # 侧边栏布局
│   │   └── ui/                    # shadcn/ui 组件（badge/button/card/dialog/input/select/sheet/skeleton/table）
│   ├── features/                  # 按功能域组织
│   │   ├── overview/              # 概览：统计卡 + 资产配比 + 手动刷新按钮
│   │   ├── holdings/              # 持仓表格 + 新增/编辑/删除 + 手动刷新按钮
│   │   ├── transactions/          # 交易记录列表
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
| 概览 | `/` | 总市值/成本/盈亏统计卡 + 资产配比条 | `GET /api/v1/holdings/with-quotes` |
| 持仓 | `/holdings` | 品种表格 + 年化回报 + 增删改操作 | `GET /api/v1/holdings/with-quotes` |
| 交易 | `/transactions` | 交易记录列表（按日期倒序） | `GET /api/v1/transactions` |
| 行情 | `/quotes` | 输入代码 + 市场选择 → 查询实时行情 | `GET /api/v1/{stock,crypto,fund}/quotes` |

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

// 业务错误
{ "code": 40001, "message": "未识别的品种代码", "data": null }

// 未找到
{ "code": 40401, "message": "持仓不存在", "data": null }
```

服务层通过抛出 `BusinessError(code, message)` 触发业务错误，全局异常处理器统一捕获。

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

### 5.7 汇率四级兜底

`utils/exchange_rate.py` 以 USD 为枢轴做币种换算，汇率来源单一（GitHub raw），故采用四级兜底保证可用性：

```
内存新鲜值（1h TTL 内）→ 网络拉取 → 内存过期旧值 → 磁盘兜底 → None
```

磁盘兜底两层（`_load_persisted` 优先读前者，没有读后者）：
- `data/exchange_rates_cache.json` — 运行时缓存，每次网络成功后覆盖写（gitignore，不进仓库）
- `data/dbjson/exchange_rates_fallback.json` — 种子文件，提交进仓库，全新环境/容器无持久卷 + 断网时的终极兜底

最坏情况（重启 + 长时间断网）也用上次成功的汇率兜底，避免概览因汇率缺失把 CNY/USD 当同币种静默算错。

### 5.8 概览行情并发拉取与熔断

`OverviewService.get_overview` 拉行情时的两个稳定性设计：

- **组间并发**：按 `(asset_class, market)` 分组后用 `asyncio.wait` 并发拉取，总耗时 ≈ 最慢一组而非串行累加
- **整体超时熔断**（`_QUOTE_FETCH_TIMEOUT = 12s`，比前端 axios 15s 略早）：超时组被取消丢弃，单组异常被吞掉，缺失品种价格兜底为 0——单个数据源抽风不拖垮整个概览，返回部分行情而非整体失败
- **汇率一次取回**：循环外 `fetch_rates()` 取一次，循环内用同步 `convert_with_rates`，消除 2N 次冗余 await

### 5.9 手动强制刷新

持仓页/概览页刷新按钮通过 `force_refresh=true` query 参数强制拉最新行情：

- 后端 `force_refresh` 从 API 一路透传到 `fetch_fund_quotes`，为 True 时跳过基金 15 分钟 DB 缓存全部走网络（股票/加密货币本就无缓存）
- 前端用 `useMutation` + `setQueryData` 实现一次性强制刷新，不污染 queryKey，60s 自动轮询仍走正常缓存

API 端点：`GET /api/v1/holdings/with-quotes?force_refresh=true`、`GET /api/v1/overview?currency=CNY&force_refresh=true`
