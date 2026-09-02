# AGENTS.md

This file provides guidance to AI coding agents (Codex, Claude Code, Cursor, etc.) when working with code in this repository.

> **🚨 严令：禁止删除数据库文件。**
>
> 以下命令**永远禁止**：
> - `rm -f data/database/assetpilot.db`
> - `rm -rf data/database/`
> - 任何删除、移动、覆盖 `data/database/` 下文件的命令
>
> 测试已使用内存 SQLite（`backend/test/conftest.py`），永远不需要碰真实 DB 文件。
> 违反此规则 = 用户持仓/交易数据丢失。**无例外。**

# AssetPilot - 个人投资看板与净值计算器

> 当前版本：V2（FastAPI + React 前后端分离）
> 架构设计：详见 [docs/architecture.md](docs/architecture.md)
> 需求文档：详见 [docs/requirements.md](docs/requirements.md)
> 数据库设计：详见 [docs/database.md](docs/database.md)
> 财务公式：详见 [docs/formulas.md](docs/formulas.md)
> 测试指南：详见 [docs/testing.md](docs/testing.md)
> 开发进度：详见 [docs/progress.md](docs/progress.md)
> 功能主规范：详见 [openspec/specs/](openspec/specs/)

## 项目目标

聚合 A股、美股、加密货币、基金的个人投资看板：
1. 实时获取持仓标的价格（腾讯财经 / Playwright + 新浪 / CoinGlass / 天天基金）
2. 记录交易流水，计算总市值和盈亏
3. 计算简单年化回报率
4. 净值走势追踪（净值快照 + 历史汇率冻结）

## 目录结构

```
backend/        FastAPI 后端（app/core + api + models + repositories + services 四层）
frontend/       React 19 SPA（api/hooks/features/components）
data/           运行时数据（database/*.db 受保护；source/ 原始数据受保护不可动）
docs/           架构/需求/数据库/公式/测试文档（评审记录在 docs/code_review/）
openspec/       OpenSpec 功能规范（changes 变更流程 + specs 主规范）
```

后端分层：`api (路由) → services (业务逻辑) → repositories (数据访问) → data_sources (外部 API)`。
核心模块清单见 [docs/requirements.md](docs/requirements.md)：概览 / 持仓 / 交易 / 行情（含自选股）/ 现金账户。

## 开发命令

```bash
# 安装依赖（仓库根）
uv venv && source .venv/bin/activate && uv pip install -e backend

# 后端启动（backend/ 目录下）
uvicorn app.main:app --reload

# 前端启动
cd frontend && npm run dev

# 全套测试（内存 SQLite，无需启动服务；必须用 .venv 的 Python）
.venv/bin/python -m pytest backend/test/

# 单个测试文件
.venv/bin/python -m pytest backend/test/test_overview_service.py -v

# 前端检查
cd frontend && npx tsc -b && npm run lint
```

## 编码约定

- **命名**：文件 `asset_quote_xxx.py` 风格（不用 `stock_xxx.py`）；类名与文件名对齐；一个文件一个类；方法用完整动词短语；变量英文
- **注释/文档**：中文，Google Style（Args / Returns）
- **类型注解**：完整 type hints（Python 3.10+ `X | None`）
- **异步优先**：所有 IO 操作用 async/await；外部调用默认并发（`asyncio.gather`），不串行 await
- **导入路径**：统一 `from app.xxx import YYY`，不用 `backend.app.xxx`
- **ORM 审计字段必填**：新建 ORM 模型必须含 `created_at / updated_at / created_by / updated_by`，缺一个就是一级事故
- **错误码统一**：所有 BusinessError 的 code 引用 `app/core/error_codes.py` 常量（40001 校验失败 / 40002 行情不可用 / 40401 不存在），禁止散落硬编码

### 外部请求超时铁律（历史事故教训）

任何后端外部请求超时**不得大于前端 axios 15s**；超时按数据特性 + 兜底情况设定（有兜底激进 3-5s、无兜底按耐心 5-8s、行情批量熔断 10-12s、Playwright 15-20s）。
所有超时值统一在 `app/core/scheduler_config.py`（SchedulerConfig）管理，不得散落硬编码。
会被高频并发调用且打同一外部慢资源的函数必须加单飞（single-flight）；端到端最坏耗时必须 < 前端超时。
事故背景详见 [docs/code_review/incident_2026-06-19_overview_timeout.md](docs/code_review/incident_2026-06-19_overview_timeout.md)。

### 受保护数据

- `data/source/` 整个目录、`data/dbjson/exchange_rates_fallback.json`（汇率种子）**不可擅自动**；前者只由用户手动管理
- 行情查询/收藏等用户界面显示的名称以品种库（asset_varieties）为准

## 核心机制（改代码前先理解）

- **后台定时预热**（`backend/app/scheduler/quote_scheduler.py`）：APScheduler 30s 拉行情 + 55min 拉汇率写缓存，**用户请求永远只读缓存**，调度器失败查 DB 历史兜底
- **行情缓存层**（`app/utils/quote_cache.py`）：进程级单例，过期数据不丢弃（用户请求永不触网）
- **行情降级**：实时失败 → DB 历史兜底（`QuoteStatus` 三态 REALTIME/HISTORICAL/UNAVAILABLE）
- **交易→持仓反推**：交易记录是唯一现金流事实源。recompute 从 0 起点回放全部交易反推持仓派生字段；建仓自动生成 buy 交易；持仓页改份额/成本自动生成勘误交易（日期=建仓日）；现金账户流水由买卖交易自动联动（现金追踪永远开）
- **市场规则**：US/CRYPTO 品种 ticker 不重复（收藏/存在性检查按 ticker）；CN 的 FUND/STOCK/ETF 可能重复（如 000001），必须按三元组 `(asset_class, market, ticker)` 精确匹配
- 财务公式（做T ROI / XIRR / Modified Dietz）见 [docs/formulas.md](docs/formulas.md)

## 协作约定

- **先讨论，后实现**：讨论方案、设计、重构策略时，没得到用户明确指令前不要动手写实现，不要新增文件或修改现有代码
- **新文件先审命名**：新增文件前先检查命名是否符合上述约定
- **受保护数据文件不可动**：违反 = 用户数据丢失
- 本文件与 CLAUDE.md 内容同步维护（后者含 Claude Code 特有细节）；两份文件不一致时以实际代码为准并提示用户

## 测试要求

- 新增功能必须配 pytest 用例（服务层为主，内存 SQLite）
- ⚠️ 写库测试的函数签名必须依赖 conftest 的 `Session` fixture（否则 patch 不建立，会写入真实数据库！）；详见 [docs/testing.md §1.3](docs/testing.md)
- 断言从"用户期望"出发（如重复创建应幂等返回而非抛异常），不从实现行为出发
- 改动后全套 `.venv/bin/python -m pytest backend/test/` 必须通过
