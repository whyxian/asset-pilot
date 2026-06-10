# AssetPilot 代码审查报告

> 审查时间：2026-06-10
> 代码规模：28 个文件，约 1368 行

---

## 🔴 严重问题

### 1. `repositories/asset_quote_repository.py:92-94` — 资源泄漏

```python
def close(self):
    self._sina.close()  # ❌ 未 await，协程被丢弃
```

`SinaDataSource.close()` 是 `async def`，但这里没有 `await`，Playwright 浏览器永远关不掉。

> ✅ **已修复：** ABC 及所有子类的 `close()` 改为 `async def`，`StockQuoteRepository.close()` 已加 `await`

### 2. `services/asset_holding_service.py:67` — 性能：每次请求新建 Service

```python
quote_svc = AssetQuoteService()  # ❌ 每次调用都新建
```

`AssetQuoteService.__init__` 会创建 StockQuoteRepository（含 TencentDataSource + 预启动 Playwright 的 SinaDataSource）、CryptoQuoteRepository、FundQuoteRepository。每次请求 `with-quotes` 都重新创建一套，非常浪费。

> ✅ **已修复：** `AssetQuoteService` 和 `AssetVarietyRepository` 改为实例字段，构造函数只创建一次

### 3. `core/data_sources.py:100-117` — 架构违规

```python
async def _fetch_us_stocks(self, codes):
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(
            select(AssetVarietyRecord.ticker, AssetVarietyRecord.name).where(...)
        )
```

数据源层直接查询数据库，违反了自身 docstring 声明的"纯获取逻辑，不涉及 DB 操作"。名称应由调用方（Repository 层）传入。

> ✅ **已修复：** DB 查询已移除，采用 `AssetVarietyRepository.get_name_map()` 在 Service 层回填

### 4. `models/orm/asset_quote_orm.py` + `asset_holding_orm.py` — 类型标注错误

> ✅ **已修复：** `price`、`change_price`、`quantity`、`cost_price`、`total_invested` 的 `Mapped[float]` 改为 `Mapped[Decimal]`

```python
# 实际是 DECIMAL(18,4)，SQLAlchemy 返回 Decimal
price: Mapped[float] = mapped_column(Numeric(18, 4), ...)  # ❌ 应为 Mapped[Decimal]
```

三个 ORM 文件都有此问题：`price`、`change_price`、`quantity`、`cost_price`、`total_invested`。

---

## 🟡 中等问题

### 5. `models/__init__.py` — 过时注释

```python
"""价格模块  # 不存在
   资产模块     # 不存在
   交易记录     # 不存在
   组合模型     # 不存在
"""
```

Docstring 引用的 `price.py`、`asset.py`、`transaction.py`、`portfolio.py` 均不存在。实际目录是 `asset_quote.py`、`asset_holding.py`、`asset_variety.py` + `orm/`。

### 6. `services/asset_holding_service.py:38` — 对象重复创建

```python
variety = await AssetVarietyRepository().get_variety(...)  # ❌ 每次都 new
```

应改用实例字段（如 `self._variety_repo`）统一管理。

### 7. `script/fetch_us_names.py:56` — 阻塞事件循环

```python
time.sleep(1)  # ❌ 阻塞整个事件循环
```

应为 `await asyncio.sleep(1)`。

### 8. `script/seed_varieties.py:29-49` — N+1 查询

```python
for idx, r in enumerate(records, 1):
    result = await session.execute(
        select(AssetVarietyRecord).where(...)  # ❌ 每条记录一次 SELECT
    )
```

对几万条记录逐条查询去重，应改为一次性批量查询。

### 9. `test/test_xueqiu.py:81-82` — 浏览器滥用

```python
async def fetch_one(item):
    async with sem:
        en = await fetch_english_name(ticker)
        # fetch_english_name → fetch_company_info → 每个 ticker 开一个全新浏览器
```

1000 个 ticker 会开 1000 个 Playwright 浏览器，应复用 browser 实例。

### 10. `test/test_xueqiu.py:107-109` — 破坏性写入

```python
if processed % 10 == 0 or processed == total:
    with open(input_path, "w") as f:  # ❌ 直接覆写输入文件
```

如果脚本在写入时崩溃，原始数据丢失。应写入临时文件。

### 11. `services/asset_quote_service.py:28-50` — 多余保存

每次行情查询都调用 `save_asset_quotes()`，包括重复的只读查询。行情数据写入应有节制（如只在首次查询时保存，或由调用方决定）。

### 12. `api/asset_quote_api.py:13` — 参数无校验

```python
async def get_stock_quotes(market: str, ...):  # ❌ 任何字符串都接受
```

应使用 `Literal["CN", "US"]` 做类型校验。

---

## 🟢 轻微问题

### 13. `main.py:18` — 未使用的 import

```python
from app.core.response import error  # 从未使用
```

### 14. `repositories/asset_quote_repository.py:4` — 未使用的 import

```python
import asyncio  # 从未使用
```

### 15. `core/data_sources.py:327` — hot path 内 import

```python
async def fetch_one(code):
    import akshare as ak  # ❌ 每次调用都重导入
```

应提到模块级别。

### 16. `core/exceptions.py:7-8` — BusinessError 缺 __str__

```python
class BusinessError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        # 缺少 __str__，日志输出难看
```

### 17. `script/convert_ticker_dot.py` — 放错目录

该文件是数据处理脚本，位于 `backend/test/` 下，应移到 `backend/script/`。

### 18. `core/data_sources.py:52` vs `:101,142` — source 命名不一致

`name` 属性返回 `"tencent"`（小写），但 `AssetQuote.source` 字段设为 `"TENCENT"`（大写）。

### 19. `models/orm/asset_quote_orm.py:24` — timestamp 命名不一致

ORM 字段名为 `timestamp`，Pydantic 模型对应字段名为 `updated_at`。

### 20. `core/data_sources.py:131` — 魔术数字

```python
if vals[0] != "200":  # "200" 是什么？
```

应定义为具名常量。

### 21. `core/database.py:33` — 缺少 shutdown 清理

```python
# 缺少 app shutdown 时调用 engine.dispose()
```

### 22. `core/database.py:13` — echo 不可配

```python
engine = create_async_engine(DB_URL, echo=False)  # 无法动态开启 SQL 日志
```

### 23. `core/logger.py:9` — 日志不包含模块名

```python
"%(asctime)s [%(levelname)s] %(message)s"  # 缺少 %(name)s
```

无法区分日志来自哪个模块。

### 24. CLAUDE.md 过时

| 部分 | 问题 |
|------|------|
| 目录结构 — models 文件 | 仍写 `models/asset_quote_orm.py`，实际在 `models/orm/` 下 |
| 目录结构 — tests | 写 `backend/tests/`（有 s），实际是 `backend/test/`（无 s） |
| 测试文件列表 | 列了 `test_fund_repo.py` 和 `test_okx_proxy.py`，这两个不存在 |
| 测试命令 | 使用 `backend/tests/` 路径，不对 |

### 25. `core/data_sources.py:189-214` — SinaDataSource 异常处理脆弱

`fetch_one()` 中如果 `browser.new_page()` 失败，`finally` 块仍引用 `page` 变量，可能导致 `NameError`。

### 26. `core/data_sources.py:168-174` — close 缺少 try/finally

如果 `_browser.close()` 抛出异常，`_playwright.stop()` 不会执行，Playwright 进程泄漏。

---

## 统计

| 级别 | 数量 |
|------|------|
| 🔴 严重 | 4 |
| 🟡 中等 | 8 |
| 🟢 轻微 | 14 |
| **合计** | **26** |
