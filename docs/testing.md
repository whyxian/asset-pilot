# AssetPilot 测试指南

> 最后更新：2026-08-05（补全 formulas/API 路由/调度器/归档/品种测试，总数 150）
> 测试目录：`backend/test/`（pytest + pytest-asyncio）

---

## 1. 测试架构

### 1.1 核心原则

| 原则 | 说明 |
|------|------|
| **内存 SQLite** | 每个测试独立 `sqlite+aiosqlite:///:memory:` 引擎，测试永不碰真实 `data/database/assetpilot.db` |
| **不触真实网络** | 所有外部资源（数据源/汇率）必须 mock 或 patch；SinaDataSource 需 Playwright 故不测 |
| **事务原子验证** | 通过 service 层事务行为验证回滚（余额不足拒绝后无残留流水等） |
| **服务层为主** | 大部分逻辑在 service 层断言；repo 直接测其独特查询；API 层测代表性端点 |

### 1.2 conftest.py 机制（理解它的工作是写测试的前提）

`backend/test/conftest.py` 提供三个核心 fixture：

- **`engine`**：每个测试独立的内存 SQLite 引擎，自动建全部表（触发所有 ORM 注册）
- **`Session`**：指向测试引擎的 `sessionmaker`，并 **monkeypatch 所有模块里缓存的 `async_session`**
  - 因为各 repo/service 在模块加载时已 `from app.core.database import async_session` 固化绑定，
    必须把每个引用它的模块属性都替换（patch 列表在 conftest 中维护——**新增模块必须同步加入**）
- **`seed_variety` / `seed_holding`**：快速灌入品种/持仓+建仓交易
  - ⚠️ `seed_holding` **自带一笔本金注入流水**（deposit = total 金额），断言现金余额时务必计入
- **`approx(a, b_str, tol="0.01")`**：Decimal 容差比较断言（`assert approx(x, "1.5")`）

### 1.3 ⚠️ 写库测试必读：Session 依赖陷阱（两起事故）

conftest 的 DB patch 只在 **`Session` fixture 建立时**执行——任何测试（包括 service 层测试）
**只要会写数据库（直接或间接调用 repo/service 的写操作），函数签名必须显式依赖 `Session`**，
否则会静默写入真实 `data/database/assetpilot.db`。

事故一（2026-08-05）：`test_api_routes.py` 的 `client` fixture 漏掉 `Session`，测试连了真实 DB（返回真实持仓数据）。

```python
@pytest.fixture
async def client(Session):   # ← 没有 Session，conftest 的 DB patch 不执行，会连真实数据库！
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

事故二（2026-08-10）：`test_watchlist_service.py::test_list_with_quotes_three_state` 签名只有
`monkeypatch`、漏掉 `Session`，其内部 `create_watchlist`（写库 + 自动注册品种）**写入真实数据库**
（watchlist 3 条 + asset_varieties 3 条），且因"重复收藏幂等"掩盖了后续泄漏——重跑测试看不出问题，
真实库数据却在增长。已修复签名并清理脏数据。

**自检规则**：写测试前先问"这个测试会写库吗？"——会，就必须有 `Session` 参数（即使只用 monkeypatch）。
不写库的纯逻辑测试（formulas、scheduler mock）可以不需要。

### 1.4 ⚠️ 断言方向检查：从用户期望出发，不从实现行为出发

事故三（2026-08-10）：`test_create_duplicate_raises` 把"重复创建品种抛异常"当预期行为写进测试——
测试全绿反而固化了 bug。真实用户路径：前端「添加到品种库」点击 QQQ（已在品种库）→ 后端撞
UNIQUE 约束 → 500。测试从"实现当前行为"出发断言了错误行为。

**写断言前先问**："用户做这个操作，什么结果才算对？"——从用户期望推断言，而非从代码现状推。
- 异常断言（`pytest.raises`）必须核对：这个场景**真的应该**是错误吗？还是应该被友好处理（幂等/兜底）？
- 新增/修改 API 时，为其"重复调用"场景写幂等测试（重复添加/重复收藏/重复建仓）
- 前后端联动按钮（收藏/添加/建仓）必须补 API 层测试——前端无自动化测试，API 层是唯一防线

## 2. 运行测试

```bash
# 全套（推荐，内存 SQLite，无需启动服务）
.venv/bin/python -m pytest backend/test/

# 单个文件
.venv/bin/python -m pytest backend/test/test_formulas.py -v

# 单个用例
.venv/bin/python -m pytest backend/test/test_cash_flow_service.py::test_deposit_withdraw_and_balance_conversion -v
```

## 3. 编写测试的约定

### 3.1 新增模块必须进 conftest patch 列表

新建 repo/service 且其内部使用 `async_session` 时，把模块路径加入 `conftest.py` 的 patch 元组，
否则测试会静默连真实数据库（现金模块就是因此长期无测试——2026-08-04 补上后才有）。

### 3.2 mock 模式

```python
# 异步方法必须用 async 函数 mock（同步 lambda 会在 await 时炸）
async def _groups():
    return {("STOCK", "CN"): ["600519"]}
monkeypatch.setattr(s._holding_repo, "list_all_tickers", _groups)

# 网络资源 patch 模块属性
monkeypatch.setattr("app.services.cash_flow_service.fetch_rates", fake_fetch_rates)

# 汇率 mock 必须含 USD 基准：{"USD": 1.0, "CNY": 7.2}
```

### 3.3 测试文件命名与风格

- 文件名：`test_<被测模块>.py`（与 `asset_quote_xxx.py` 命名规范一致）
- 中文 docstring 说明被测行为与期望值推导（含注释里的数学过程）
- 分组注释：`# ═══...═══` 分隔场景块
- 断言用 `approx`（Decimal 容差），不直接 `==` 浮点

## 4. 覆盖矩阵（2026-08-05）

| 模块 | 测试文件 | 用例数 | 关键覆盖点 |
|------|---------|--------|-----------|
| 交易重算/归档 | `test_transaction_recompute.py` | 8 | 基线/买入/卖出/卖超/清仓/归档/白拿股票 |
| 持仓服务 | `test_asset_holding_service.py` | 10 | CRUD + 建仓现金联动 + 级联删除 + 行情分发 |
| 交易服务 | `test_transaction_service.py` | 10 | 校验链 + 事务回滚 + 归档触发 + 现金联动 |
| 汇率工具 | `test_exchange_rate.py` | 11 | 五级兜底 + 单飞 + CNY 直通 |
| 概览服务 | `test_overview_service.py` | 8 | 年化 + USD 聚合 + 行情并发熔断 |
| 行情服务 | `test_asset_quote_service.py` | 15 | 缓存命中 + force_refresh + DB 历史降级 |
| 数据源 | `test_data_sources.py` | 8 | 腾讯/CoinGlass/天天基金/akshare 解析 |
| 行情缓存 | `test_quote_cache.py` | 6 | get/set/过期不丢/部分命中 |
| 交易时段 | `test_trading_hours.py` | 8 | 三市场时段判定 + TTL 兜底 |
| 品种仓库 | `test_asset_variety_repository.py` | 5 | 搜索相关性排序 |
| 行情仓库 | `test_asset_quote_repository.py` | 4 | 去重 + 时间窗口 |
| 快照服务 | `test_snapshot_service.py` | 6 | 双表写 + FX 冻结 + 幂等 |
| 现金流水 | `test_cash_flow_service.py` | 10 | 入金出金/余额换算/建仓/勘误/删持仓/买卖联动 |
| 财务公式 | `test_formulas.py` | 18 | 做T ROI / 组合聚合 / XIRR / Modified Dietz |
| 品种服务 | `test_asset_variety_service.py` | 5 | CRUD + 软删除 + 搜索排序 |
| 归档服务 | `test_closed_holding_service.py` | 5 | 分页/详情/删除连带删流水 |
| API 路由 | `test_api_routes.py` | 8 | 统一返回格式 + 错误码 + 代表性端点 |
| 定时调度 | `test_quote_scheduler.py` | 9 | 刷新频率 + 预热 + DB 历史兜底 |
| 自选股 | `test_watchlist_service.py` | 8 | 收藏自动注册品种/幂等/取消/三态行情 |

**合计 164 个用例。**

## 5. 未覆盖说明

| 模块 | 原因 |
|------|------|
| `SinaDataSource` | 依赖 Playwright 浏览器，测试环境不启动 |
| `core/logger.py`、`core/scheduler_config.py` | 纯常量/日志薄层，收益低 |
| `api/` 行情端点（quotes） | 依赖真实数据源，被 service 层测试覆盖；如需可 mock 后补 |
| `core/database.py` | 建表逻辑被所有测试间接覆盖（engine fixture） |
| `script/` 数据导入脚本 | 一次性运维脚本 |

## 6. 新增/修改测试时的自检清单

- [ ] 新模块进了 conftest patch 列表
- [ ] 未触真实 DB / 网络
- [ ] API 测试的 client fixture 依赖 Session
- [ ] 异步方法 mock 用了 async 函数
- [ ] 断言用 approx 而非浮点 ==
- [ ] 全套 `pytest backend/test/` 通过
