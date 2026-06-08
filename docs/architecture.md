# AssetPilot V2 架构设计

> 版本：v2.1
> 最后更新：2026-06-07

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
│   ├── tests/          #   测试
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/           # 前端 SPA（规划中，React + Vite）
├── data/               # 运行时数据（SQLite 数据库文件）
├── docs/               # 文档
│   ├── architecture.md
│   ├── requirements.md
│   └── database.md
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
│   │   └── asset_variety_api.py   # 品种目录 CRUD
│   ├── models/                    # 数据模型
│   │   ├── asset_quote.py         # AssetQuote (Pydantic)
│   │   ├── asset_quote_orm.py     # AssetQuoteRecord (SQLAlchemy)
│   │   ├── asset_holding.py       # AssetHolding (Pydantic)
│   │   ├── asset_holding_orm.py   # AssetHoldingRecord (SQLAlchemy)
│   │   ├── asset_variety.py       # AssetVariety (Pydantic)
│   │   └── asset_variety_orm.py   # AssetVarietyRecord (SQLAlchemy)
│   ├── repositories/              # 数据访问层
│   │   ├── asset_quote_repository.py  # 行情 Repo（调用 DataSource）
│   │   ├── asset_holding_repository.py# 持仓 CRUD
│   │   └── asset_variety_repository.py# 品种目录 CRUD
│   └── services/                  # 业务逻辑层
│       ├── asset_quote_service.py # 行情业务逻辑
│       ├── asset_holding_service.py# 持仓业务逻辑
│       └── asset_variety_service.py# 品种目录业务逻辑
├── tests/
│   ├── test_stock_api.py
│   └── test_fund_repo.py
└── Dockerfile
```

### 3.3 前端（已初始化）

SPA 单页应用 + 侧边栏布局（后续可扩展顶部导航模式）。当前使用 JSON 数据展示，后端 API 完成后切换。

```
frontend/
├── src/
│   ├── api/                       # API 客户端（待对接后端）
│   ├── components/
│   │   ├── layout/                # 侧边栏布局
│   │   └── ui/                    # shadcn/ui 组件（button, card, table 等）
│   ├── data/                      # JSON 示例数据（临时，后续替换）
│   ├── features/                  # 按功能域组织
│   │   ├── overview/              # 概览：统计卡 + 净值走势 + 资产配比
│   │   ├── holdings/              # 持仓：品种盈亏列表
│   │   ├── transactions/          # 交易：增删改查
│   │   └── quotes/                # 行情：输入代码查实时价
│   ├── routes/
│   ├── types/
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

页面视图：

| 视图 | 路由 | 内容 |
|------|------|------|
| 概览 | `/` | 总市值/成本/盈亏统计卡 + 净值走势 + 资产配比 |
| 持仓 | `/holdings` | 各品种表格：代码、名称、市场、持仓量、成本、现价、市值、盈亏 |
| 交易 | `/transactions` | 交易记录列表（按日期倒序） |
| 行情 | `/quotes` | 输入代码查询实时行情 |

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

- A 股 / 加密货币 / 基金：httpx async + `asyncio.gather` 并发
- 美股：Playwright async API，浏览器单例复用

### 5.3 多数据源切换

每个 Repository 支持通过 `source` 参数切换数据源：

```python
quotes = await repo.fetch_realtime_quote(["166002"])               # 默认源
quotes = await repo.fetch_realtime_quote(["166002"], source="akshare")  # ak share
```

当前实现的数据源（按 `supports(asset_class, market)` 路由）：

| DataSource | name | 覆盖范围 |
|-----------|------|---------|
| `TencentDataSource` | `tencent` | STOCK + A / STOCK + US |
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
