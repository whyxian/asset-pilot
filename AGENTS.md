# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

> **🚨 严令：禁止删除数据库文件。**
> 
> 以下命令**永远禁止**：
> - `rm -f data/database/assetpilot.db`
> - `rm -rf data/database/`
> - 任何删除、移动、覆盖 `data/database/` 下文件的命令
> 
> 测试已使用内存 SQLite（`conftest.py`），永远不需要碰真实 DB 文件。
> 违反此规则 = 用户持仓/交易数据丢失。**无例外。**

# AssetPilot - 个人投资看板与净值计算器

> 当前版本：V2（FastAPI + React 前后端分离，开发中）
> 架构设计：详见 [docs/architecture.md](docs/architecture.md)
> 需求文档：详见 [docs/requirements.md](docs/requirements.md)
> 数据库设计：详见 [docs/database.md](docs/database.md)
> 开发进度：详见 [docs/progress.md](docs/progress.md)

## 项目目标
一个聚合 A股、美股、加密货币、基金的个人投资看板，核心功能：
1. 实时获取持仓标的价格（腾讯财经 / Playwright + 新浪 / CoinGlass / 天天基金）
2. 记录交易流水，计算总市值和盈亏
3. 计算简单年化回报率
4. 净值走势追踪（净值快照 + 历史汇率冻结）

## 目录结构

```
AssetPilot/
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口 + lifespan + CORS + 全局异常处理
│   │   ├── core/                    # 基础设施
│   │   │   ├── database.py          # SQLAlchemy 引擎 + init_db
│   │   │   ├── data_sources.py      # 数据源层：腾讯/新浪/CoinGlass/天天基金/akshare
│   │   │   ├── scheduler_config.py  # 统一配置：调度间隔/缓存TTL/网络超时（SchedulerConfig）
│   │   │   ├── exceptions.py        # BusinessError 自定义异常
│   │   │   ├── logger.py            # 统一日志模块
│   │   │   └── response.py          # ApiResponse 统一返回格式
│   │   ├── api/
│   │   │   ├── asset_quote_api.py   # 行情接口（A股/美股/加密货币/基金）
│   │   │   ├── asset_holding_api.py # 持仓 CRUD 接口
│   │   │   ├── asset_variety_api.py # 品种目录接口
│   │   │   ├── transaction_api.py   # 交易记录 CRUD
│   │   │   ├── overview_api.py      # 概览统计（汇率换算聚合）
│   │   │   ├── snapshot_api.py      # 净值快照（组合级 + 品种级）
│   │   │   └── closed_holding_api.py# 历史持仓归档
│   │   ├── models/
│   │   │   ├── asset_quote.py       # AssetQuote (Pydantic)
│   │   │   ├── asset_holding.py     # AssetHolding / HoldingWithQuote (Pydantic)
│   │   │   ├── asset_variety.py     # AssetVariety (Pydantic)
│   │   │   ├── transaction.py       # Transaction / Create / Update (Pydantic)
│   │   │   ├── overview.py          # OverviewStats / AllocationItem (Pydantic)
│   │   │   └── orm/                 # SQLAlchemy ORM
│   │   │       ├── asset_quote_orm.py
│   │   │       ├── asset_holding_orm.py
│   │   │       ├── asset_variety_orm.py
│   │   │       ├── transaction_orm.py
│   │   │       ├── asset_snapshot_orm.py
│   │   │       ├── networth_snapshot_orm.py
│   │   │       └── closed_holding_orm.py
│   │   ├── repositories/
│   │   │   ├── asset_quote_repository.py  # 行情 Repo（调用 DataSource）
│   │   │   ├── asset_holding_repository.py# 持仓 CRUD
│   │   │   ├── asset_variety_repository.py# 品种目录 CRUD
│   │   │   ├── transaction_repository.py  # 交易记录 CRUD
│   │   │   ├── snapshot_repository.py     # 净值快照读写
│   │   │   └── closed_holding_repository.py# 历史持仓归档
│   │   ├── services/
│   │   │   ├── asset_quote_service.py     # 行情业务逻辑（基金 15min 缓存 + force_refresh）
│   │   │   ├── asset_holding_service.py   # 持仓业务逻辑（含市值/盈亏/年化计算）
│   │   │   ├── asset_variety_service.py   # 品种目录业务逻辑
│   │   │   ├── transaction_service.py     # 交易业务逻辑（交易记录写入 + recompute 反推持仓）
│   │   │   ├── overview_service.py        # 概览（行情并发拉取 + 超时熔断 + 汇率聚合）
│   │   │   ├── snapshot_service.py        # 净值快照（双表写 + 历史 FX 冻结）
│   │   │   └── closed_holding_service.py  # 历史持仓归档
│   │   └── utils/
│   │       ├── exchange_rate.py     # 汇率工具（五级兜底 + 单飞）
│   │       ├── quote_cache.py       # 行情内存缓存（进程级单例）
│   │       └── trading_hours.py     # 交易时段判定
│   ├── scheduler/                   # 后台定时任务（APScheduler）
│   │   └── quote_scheduler.py       # 行情30s + 汇率55min 定时预热
│   ├── script/                      # 数据导入/处理脚本
│   └── test/                        # pytest + pytest-asyncio 单元测试（内存 SQLite）
├── frontend/                        # React 19 SPA（已对接后端 API）
│   └── src/
│       ├── api/                     # Axios 客户端 + endpoints
│       ├── hooks/                   # TanStack Query hooks
│       ├── features/                # overview / holdings / transactions / quotes
│       ├── components/ui/           # Base UI + Tailwind 组件
│       └── routes/
├── data/
│   ├── database/assetpilot.db       # SQLite (自动创建)
│   ├── dbjson/                      # 品种数据 JSON + 汇率种子兜底文件
│   └── source/                      # 原始数据（受保护，不可动）
├── docs/
│   ├── architecture.md
│   ├── requirements.md
│   ├── database.md
│   └── progress.md
└── AGENTS.md
```

## 开发命令

### 安装依赖

```bash
cd /home/xian/workspace/01-ai/03-asset-pilot/
uv venv
source .venv/bin/activate
uv pip install -e backend
uv pip install playwright && playwright install chromium
```

### 启动服务

```bash
# 后端
uvicorn app.main:app --reload
# 前端
cd frontend && npm run dev
```

### 运行测试

```bash
# 全套 pytest（内存 SQLite，无需启动服务）
.venv/bin/python -m pytest backend/test/
# 单个测试文件
.venv/bin/python -m pytest backend/test/test_overview_service.py -v
```

## 四层架构

```
api (HTTP 路由) → services (业务逻辑) → repositories (数据访问) → data_sources (外部 API)
```

| 层 | 目录 | 职责 |
|----|------|------|
| **middleware** | `app/main.py` | CORS / 请求日志 / 全局异常处理 |
| **api** | `app/api/` | HTTP 路由，参数校验，调用 service，返回 ApiResponse |
| **services** | `app/services/` | 业务逻辑编排，抛出 BusinessError |
| **repositories** | `app/repositories/` | 数据访问，调用 DataSource 或操作 DB |
| **data_sources** | `app/core/data_sources.py` | 纯行情获取逻辑，不涉及 DB。通过 `supports()` 声明支持的 asset_class + market |

## 编码约定

### 命名规范

- **文件命名**：用 `asset_quote_xxx.py` 而非 `stock_xxx.py`，命名要详细清晰
- **类命名**：与文件名对齐。文件 `asset_quote_service.py` → 类 `AssetQuoteService`
- **一个文件一个类**：模型文件只定义一个类（如 `AssetQuote`）
- **方法命名**：完整动词短语，如 `save_asset_quotes` 而非 `save_quotes`
- **变量**：用英文，如 `market` 而非 `market_type`
- **注释/文档**：用中文，Google Style（Args / Returns）

### 风格

- **类型注解**：完整 type hints（Python 3.10+ `X | None` 语法）
- **异步优先**：所有 IO 操作用 `async/await`
- **导入路径**：统一用 `from app.xxx import YYY`，不用 `backend.app.xxx`

### 外部请求超时规范

> 起因：2026-06-19 概览接口超时事故——汇率请求 20s 超时 > 前端 15s 超时，导致前端反复超时报错。详见 [docs/code_review/incident_2026-06-19_overview_timeout.md](docs/code_review/incident_2026-06-19_overview_timeout.md)。

外部请求（httpx / Playwright 等）的超时**必须按数据特性 + 兜底情况设定，不得拍脑袋**：

| 类型 | 原则 | 参考值 |
|------|------|--------|
| 小 JSON / API（有兜底） | 兜底充足就敢设短，失败立刻回退 | 3-5s |
| 小 JSON / API（无兜底） | 按用户耐心 | 5-8s |
| 行情批量（多数据源并发） | 整体熔断阈值 | 10-12s |
| 浏览器渲染（Playwright） | 渲染本就慢 | 15-20s |

**铁律：任何后端外部请求超时不得大于前端超时（当前 axios 15s）。** 否则后端慢点必然导致前端超时。所有超时值统一在 [SchedulerConfig](backend/app/core/scheduler_config.py) 管理，不得散落硬编码。

配套要求：
- **兜底与超时配套**：有内存/磁盘/种子兜底的外部资源，超时应激进（几秒），让失败快速回退；无兜底才保守。
- **单飞**：会被高频并发调用、且每次打同一外部慢资源的函数，必须加单飞（single-flight，如 `exchange_rate.fetch_rates` 的 `_inflight` task），N 个请求只发 1 个网络请求。
- **独立资源并发化**：service 层多个互不依赖的外部调用，默认 `asyncio.gather` 并发，不得串行 `await`（最坏耗时取 max 而非累加）。
- **端到端超时链校验**：单接口最坏耗时（串行外部调用超时之和 / 并发取最大）必须 < 前端超时。code review 时检查。

### 协作流程

- **讨论阶段不要写代码**：讨论方案、设计、重构策略时，没得到明确指令前不要动手写实现，更不要新增文件或修改现有代码。等我先确认方案再动。**先讨论，后实现。**
- **新文件先审命名**：新增文件之前，先检查命名是否符合本规范的命名约定（文件命名、类命名、方法命名），确认后再创建。防止出现 `quote_api.py` 这种不遵循 `asset_quote_xxx.py` 模式的命名。
- **ORM 审计字段必填**：新建 ORM 模型时必须包含完整的审计字段（`created_at`, `updated_at`, `created_by`, `updated_by`），与 database.md 中的约定一致。缺一个就是一级事故。
- **受保护数据文件**：`data/source/` 整个目录、`data/dbjson/exchange_rates_fallback.json`（汇率种子兜底）不可擅自动。`data/source/` 只由用户手动管理；汇率种子文件更新需用户确认。
- **代码审查用 checklist**：审查（含自审）时按 [docs/code_review/CHECKLIST.md](docs/code_review/CHECKLIST.md) 逐条检查，不得靠「扫代码」凭感觉。重点：超时链（§一）、并行机会（§二）这两类需跨层对比才能发现的问题，是历史事故高发区，必须强制过。

## 核心功能模块

详见 [docs/requirements.md](docs/requirements.md)

1. 概览 — 组合级统计卡 + 净值走势 + 资产配比
2. 持仓 — 品种盈亏列表（实时行情驱动）
3. 交易 — 交易记录 CRUD（辅助功能）
4. 行情 — 四市场实时价格查询

## 数据源架构

每个数据源独立一个类，通过 `supports(asset_class, market)` 声明能力：

| DataSource | 覆盖范围 |
|-----------|---------|
| `TencentDataSource` | STOCK+CN / STOCK+US / FUND+US |
| `SinaDataSource` | STOCK + 美股（Playwright 备选） |
| `CoinGlassDataSource` | CRYPTO |
| `EastMoneyFundDataSource` | FUND（天天基金 pingzhongdata） |
| `AkshareFundDataSource` | FUND（akshare 备选） |

汇率源（`app/utils/exchange_rate.py`）：GitHub raw（USD 为基准，每小时更新）。五级兜底 + 单飞保证可用性：**内存新鲜值（1h TTL）→ 网络拉取 → 内存过期旧值 → 运行时缓存 → 种子文件 → 硬编码常量**，`fetch_rates` 永不返回 None。详见 [architecture.md §5.7](docs/architecture.md)。

## 关键机制

- **后台定时预热**（`app/scheduler/quote_scheduler.py`）：APScheduler 后台定时拉行情(30s)+汇率(55min)写缓存，**用户请求永远只读缓存**，与数据源彻底解耦。调度器失败查 DB 历史兜底，保证缓存永不过期。详见 [architecture.md §5.11](docs/architecture.md)。
- **行情缓存层**（`app/utils/quote_cache.py`）：进程级单例，单 ticker 粒度 + 部分命中，过期数据不丢弃（用户请求永不触网）。
- **行情降级兜底**：实时失败 → DB 历史兜底（`QuoteStatus` 三态 REALTIME/HISTORICAL/UNAVAILABLE），前端按状态标记。
- **统一配置**（`app/core/scheduler_config.py`）：`SchedulerConfig` 集中管理调度间隔/缓存TTL/网络超时，铁律「后端外部请求超时 ≤ 前端 axios 15s」。
- **手动刷新**：`force_refresh=true` 跳过缓存读 + 走网络 + **写缓存**（保持刷新后读取一致）。
- **概览稳定性**：`overview_service` 行情组并发拉取 + 12s 超时熔断 + 单组异常容错，单个数据源抽风不拖垮整个概览。
- **交易→持仓反推**：交易记录是唯一现金流事实源（为 XIRR 铺路）。建仓自动生成 buy 交易，recompute 从 0 起点回放全部交易反推持仓派生字段（quantity/cost_price/total_invested）。持仓页手动改份额/成本自动生成勘误交易（日期=建仓日，XIRR 影响最小）。initial_* 基线已废弃删除。
