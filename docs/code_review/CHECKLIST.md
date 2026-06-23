# AssetPilot 代码审查 Checklist

> 用法：每次代码审查（含自审）按本清单逐条检查。每条给出「检查方法」和「反例」。
> 起因：2026-06-19 概览接口超时事故暴露——靠「扫代码找问题」会漏掉跨层超时链、并行机会这类需横向对比才能发现的问题。本清单把这类检查强制化。
> 配套：超时分级原则见 [CLAUDE.md §外部请求超时规范](../CLAUDE.md)；事故复盘见 [incident_2026-06-19_overview_timeout.md](code_review/incident_2026-06-19_overview_timeout.md)。

---

## 一、超时与可靠性（事故高发区，优先级最高）

### ☐ 1.1 后端外部请求超时 ≤ 前端超时（15s）

**检查方法**：grep 所有 `timeout=`，列出每个值。任一 > 15s 即一级问题。

**反例**：汇率 `httpx.AsyncClient(timeout=20)` —— 后端 20s > 前端 15s，连不上时前端先超时，用户看到加载失败。

### ☐ 1.2 兜底与超时配套

**检查方法**：对每个有兜底（内存/磁盘/种子/硬编码）的外部资源，确认其超时是否激进（几秒）。有兜底还设长超时 = 自相矛盾。

**反例**：汇率五级兜底齐全，却设 20s 超时——等于「宁可让用户等 20s 也要拿最新汇率」，与兜底设计矛盾。应 3-5s。

### ☐ 1.3 端到端超时链校验

**检查方法**：对改动涉及的接口，算「最坏耗时」= 串行外部调用超时之和（并发的取 max）。结果必须 < 前端 15s。否则接口在某些情况下必然触发前端超时。

**反例**：overview 行情 12s（熔断）+ 汇率 20s 串行 = 32s 最坏，远超 15s。改并发后 max(12,5)=12s < 15s。

### ☐ 1.4 单飞（single-flight）

**检查方法**：找出「会被高频并发调用 + 每次打同一外部慢资源」的函数。判断标准：N 个请求并发时会不会发 N 个网络请求？会 → 必须单飞。

**反例**：`fetch_rates` 被 60s 轮询 + 前端重试并发调用，无单飞时 3 个请求各发各的、各卡满超时。加 `_inflight` task 后 N 个请求复用 1 个网络调用。

### ☐ 1.5 超时熔断后的资源清理

**检查方法**：`asyncio.wait` 超时或 `task.cancel()` 后，是否 `await asyncio.gather(*pending, return_exceptions=True)` 收尾？不收尾会留「Task was destroyed but pending」警告 + 连接清理时机不确定。

**反例**：`_fetch_quote_map` 超时 cancel 后未 await，被审查发现后补上。

---

## 二、并行机会（事故第二高发区）

### ☐ 2.1 列出函数内所有 await 外部 IO，两两问「能并发吗」

**检查方法**：对每个 service 方法，列出所有 `await 外部调用`（网络/DB/汇率）。**不只看 for 循环内的串行，要看所有顶层独立 await**。两两判断有无数据依赖，无依赖却串行 = 问题。

**反例①（循环内串行）**：`for groups: await fetch_quotes_by_asset_class()` —— 各组独立网络调用，应 `asyncio.gather`。
**反例②（顶层独立 await 串行，更易漏）**：overview 里 `await fetch_quote_map_concurrent()` 后接 `await fetch_rates()`，两者无依赖却串行。**第一次审查只盯循环模式，漏了这种。**

### ☐ 2.2 同一事务内的 await 不可并发

**检查方法**：确认串行的 await 是否因为共享同一 `AsyncSession`/事务。是则必须串行（SQLite 单写 + session 非并发安全），不算问题。

**正例**：`transaction_service` 的 `recompute_holding` 循环操作同一 session，串行正确，不强行并发。

### ☐ 2.3 session.add/delete 循环不算串行问题

**检查方法**：`for x: await session.add(x)` / `session.delete(x)` 是内存操作（commit 时才落库），不是真 IO 串行，无需改。

---

## 三、正确性常规

### ☐ 3.1 异步资源用 async/await，不阻塞事件循环

**检查方法**：grep `time.sleep`、同步 `requests`、同步文件 IO 在 async 函数内的使用。应用 `asyncio.sleep` / `httpx.AsyncClient` / `asyncio.to_thread`。

### ☐ 3.2 key 冲突审查

**检查方法**：dict 用业务 key 时，确认 key 能否跨类别冲突。多个类别共用同一 key 空间 → 用复合 key（如三元组）。

**反例**：`quote_map[q.ticker]` 单 key，000001 既是 A 股又是基金会互相覆盖。改 `(ac, market, ticker)` 三元组。

### ☐ 3.3 falsy 误判

**检查方法**：`x or y` / `if x:` 用在可能是空容器/0/空字符串的值上时，确认是否该用 `is None` / `is not None`。

**反例**：`payload.get("rates") or payload.get("datas")` —— rates 为空 dict `{}`（falsy）会误回退到 datas。改 `is None` 判断。

### ☐ 3.4 静默失败

**检查方法**：函数失败时是返回默认值/None 还是抛错？返回默认值的情况下，调用方是否意识到拿到了「降级数据」？涉及钱/数值计算的降级，必须有日志或向上透传标志位，不能静默。

**反例**：汇率全不可用时 `rates or {}` 静默算错（CNY/USD 当同币种相加）。后改为五级兜底 + is_stale 标志透传前端。

---

## 四、项目硬约束（违反即一级事故）

### ☐ 4.1 命名规范

- 文件：`asset_quote_xxx.py` 而非 `stock_xxx.py`，详细清晰
- 类：与文件名对齐（`asset_quote_service.py` → `AssetQuoteService`）
- 方法：完整动词短语（`save_asset_quotes` 而非 `save_quotes`）
- 变量：英文（`market` 而非 `market_type`）
- 新增文件前先审命名

### ☐ 4.2 ORM 审计字段必填

新建 ORM 模型必须含 `created_at` / `updated_at` / `created_by` / `updated_by`，与 database.md 一致。缺一个 = 一级事故。

### ☐ 4.3 受保护数据文件

`data/source/` 整个目录、`data/dbjson/exchange_rates_fallback.json` 不可擅自动。涉及前先确认。

### ☐ 4.4 注释中文 + Google Style

注释/文档用中文，Google Style（Args / Returns）。

### ☐ 4.5 类型注解完整

完整 type hints，Python 3.10+ `X | None` 语法。

---

## 五、测试

### ☐ 5.1 改动有对应测试

新增/修改的逻辑分支（含兜底分支、并发分支、异常分支）是否有测试覆盖？

### ☐ 5.2 mock 签名与真实签名一致

mock 的函数签名（参数名、关键字参数）是否与真实函数一致？签名漂移会导致测试通过但实际调用报错。

**反例**：mock `fetch_quotes_by_asset_class(ac, market, tickers)` 漏了 `force_refresh` 参数，真实调用带该参数时报 TypeError。

### ☐ 5.3 全套测试通过 + tsc 通过

`.venv/bin/python -m pytest backend/test/` 全绿；`cd frontend && npx tsc --noEmit` 无错。

---

## 六、后端数据校验（CR 必查）

> **铁律：前端传过来的一切数据都不可信。** 后端必须独立校验，不能假设前端做了校验就不重复做。
> 不一致的数据 = 脏数据，**拒绝写入**，不是"存了再说"。
> Pydantic `Field(gt=0)` 等约束是第一道防线，service 层一致性验算是第二道。

### ☐ 6.1 数值范围校验

**检查方法**：每个接受用户输入的 Pydantic 模型，检查数值字段是否有 `Field(gt=0)` / `Field(ge=0)` 等约束。无约束的数值字段 = 问题。

**反例**：`AssetHoldingCreate.quantity: Decimal` 没有 `gt=0`，用户传 0 或负数直接入库。

### ☐ 6.2 字段间一致性验算

**检查方法**：对每个涉及多字段关系的写入接口（create/update），检查 service 层是否验算字段间的一致性。不一致时 `raise BusinessError` 拒绝写入。

**必须验算的关系**：
- 建仓：`total_invested == quantity × cost_price`（误差 > 0.01 拒绝）
- 交易：`amount == quantity × unit_price × (1 + fee_rate/100)`（误差 > 0.01 拒绝）
- 交易：`fee_rate` 范围 0~100

**反例**：交易表单前端算出 `amount = qty × price + 手续费`，但用户手改 amount 为乱值，后端不验算直接存入 → DB 里 `amount` 和 `qty × price` 对不上 → recompute 和 Modified Dietz 算出不同结果。

### ☐ 6.3 update 操作合并验算

**检查方法**：update 接口只传部分字段时，service 层是否把新旧值合并后再验算。

**反例**：编辑交易只传了 `fee_rate`，没传 `amount`。后端只校验 `fee_rate` 范围，不合并旧的 `amount` 验算一致性 → 改了费率但金额没跟着改，脏数据入库。

### ☐ 6.4 精度一致性

**检查方法**：金额类字段（Decimal）在 service → formulas → DB 全链路是否有 `float()` 转换。有 = 问题。

**反例**：`float(h.cost_price)` 传给公式 → 公式内部 float 算术 → `Decimal(str(float))` 回来 → 精度损失累积，两条路径算同一金额差 ¥21。

---

## 七、文档同步

### ☐ 7.1 改动涉及的文档已更新

涉及架构/接口/数据库/进度的改动，同步更新 docs/ 对应文档（architecture / progress / database / requirements）和 CLAUDE.md。

### ☐ 7.2 过时引用已清理

删除的文件/重命名的函数/改过的命令，文档里是否还有残留引用？（如 CLAUDE.md 曾引用已删的 `test_stock_api.py`）

---

## 审查记录

每次审查填写：审查范围（commit/PR）、逐条结果、发现的问题清单、修复状态。模板见 [docs/code_review/](code_review/) 历史报告。
