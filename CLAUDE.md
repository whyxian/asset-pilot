# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# AssetPilot - 个人投资看板与净值计算器

> 当前版本：V2 (FastAPI 后端开发中)
> 设计稿：详见 [docs/architecture.md](docs/architecture.md)（React + FastAPI + SQLite 前后端分离）
> 需求文档：详见 [docs/requirements.md](docs/requirements.md)
> 数据库设计：详见 [docs/database.md](docs/database.md)

## 项目目标
一个聚合 A股、美股、加密货币、基金的个人投资看板，核心功能：
1. 实时获取持仓标的价格（腾讯财经 / Playwright + 新浪 / CoinGlass / 天天基金）
2. 记录交易流水，计算总市值和盈亏
3. 计算简单年化回报率
4. 净值走势追踪

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
│   │   │   ├── exceptions.py        # BusinessError 自定义异常
│   │   │   ├── logger.py            # 统一日志模块
│   │   │   └── response.py          # ApiResponse 统一返回格式
│   │   ├── api/
│   │   │   ├── asset_quote_api.py   # 行情接口（A股/美股/加密货币/基金）
│   │   │   ├── asset_holding_api.py # 持仓 CRUD 接口
│   │   │   └── asset_variety_api.py # 品种目录接口
│   │   ├── models/
│   │   │   ├── asset_quote.py       # AssetQuote (Pydantic)
│   │   │   ├── asset_quote_orm.py   # AssetQuoteRecord (SQLAlchemy)
│   │   │   ├── asset_holding.py     # AssetHolding (Pydantic)
│   │   │   ├── asset_holding_orm.py # AssetHoldingRecord (SQLAlchemy)
│   │   │   ├── asset_variety.py     # AssetVariety (Pydantic)
│   │   │   └── asset_variety_orm.py # AssetVarietyRecord (SQLAlchemy)
│   │   ├── repositories/
│   │   │   ├── asset_quote_repository.py  # 行情 Repo（调用 DataSource）
│   │   │   ├── asset_holding_repository.py# 持仓 CRUD
│   │   │   └── asset_variety_repository.py# 品种目录 CRUD
│   │   └── services/
│   │       ├── asset_quote_service.py     # 行情业务逻辑
│   │       ├── asset_holding_service.py   # 持仓业务逻辑
│   │       └── asset_variety_service.py   # 品种目录业务逻辑
│   ├── tests/
│   │   ├── test_stock_api.py        # 行情接口测试
│   │   ├── test_fund_repo.py        # 基金净值测试
│   │   └── test_okx_proxy.py        # akshare 测试
├── frontend/                    # React SPA (规划中)
├── data/
│   └── database/
│       └── assetpilot.db         # SQLite (自动创建)
├── docs/
│   ├── architecture.md
│   ├── requirements.md
│   └── database.md
└── CLAUDE.md
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
uvicorn app.main:app --reload
# 或 PyCharm Debug backend/app/main.py
```

### 运行测试

```bash
.venv/bin/python backend/tests/test_stock_api.py    # 需先启动服务
.venv/bin/python backend/tests/test_fund_repo.py     # 直接运行，无需启动服务
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

### 协作流程

- **讨论阶段不要写代码**：讨论方案、设计、重构策略时，没得到明确指令前不要动手写实现，更不要新增文件或修改现有代码。等我先确认方案再动。**先讨论，后实现。**
- **新文件先审命名**：新增文件之前，先检查命名是否符合本规范的命名约定（文件命名、类命名、方法命名），确认后再创建。防止出现 `quote_api.py` 这种不遵循 `asset_quote_xxx.py` 模式的命名。
- **ORM 审计字段必填**：新建 ORM 模型时必须包含完整的审计字段（`created_at`, `updated_at`, `created_by`, `updated_by`），与 database.md 中的约定一致。缺一个就是一级事故。

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
| `TencentDataSource` | STOCK + A 股 / STOCK + 美股 |
| `SinaDataSource` | STOCK + 美股（Playwright 备选） |
| `CoinGlassDataSource` | CRYPTO |
| `EastMoneyFundDataSource` | FUND（天天基金 pingzhongdata） |
| `AkshareFundDataSource` | FUND（akshare 备选） |
