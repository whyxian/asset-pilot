# AssetPilot 开发进度

> 最后更新：2026-08-04（现金账户管理 + 全系统表格分页 + 前端质量清理）
> 记录所有模块的完成状态、任务拆分和开发规划

---

## 一、开发路线图

```
Phase 1 ──→ Phase 1a ──→ Phase 1b ──→ Phase 2 ──→ Phase 4 ──→ 持仓 UI ──→ Phase 5 ──→ 交易→持仓自动反推
 持仓CRUD     品种验证      数据填充      持仓计算      前端对接     增删改      交易CRUD       建仓基线 + 全量重算
   └──→ 净值快照 ──→ 现金账户 ──→ 表格分页
         双表+FX冻结    流水+买卖联动     4 列表接入
```

| 阶段 | 内容 | 完成时间 | 状态 |
|------|------|---------|------|
| Phase 1 | 持仓 ORM + CRUD | 2026-06-07 | ✅ |
| Phase 1a | 品种验证（asset_varieties 表+API） | 2026-06-07 | ✅ |
| Phase 1b | 品种数据填充（45884 条，四市场全覆盖） | 2026-06-10 | ✅ |
| Phase 2 | 持仓计算服务（with-quotes API） | 2026-06-07 | ✅ |
| Phase 4 | 前后端对接（4 页切到真实 API） | 2026-06-10 | ✅ |
| 持仓 UI | 增删改对话框 + 品种搜索自动填充 | 2026-06-11 | ✅ |
| Phase 5 | 交易记录 CRUD（后端+前端） | 2026-06-10 | ✅ |
| 概览 API | GET /api/v1/overview（后端聚合 + 汇率换算） | 2026-06-11 | ✅ |
| 汇率工具 | exchange_rate.py（GitHub 源 + 1h 缓存） | 2026-06-11 | ✅ |
| 精度修复 | 前端数字格式化 T0 级重写 | 2026-06-11 | ✅ |
| 数据自动刷新 | 概览/持仓页 60s 轮询 + 持仓变更联动失效概览缓存 | 2026-06-13 | ✅ |
| 交易→持仓自动反推 | 建仓基线 + 全量重算（加权平均/卖超拒绝/事务原子）+ 交易页 CRUD UI | 2026-06-13 | ✅ |
| 单元测试补齐 | 65 个 pytest 用例覆盖 service/repo/data_source/exchange_rate | 2026-06-15 | ✅ |
| Phase 6 净值快照 | networth_snapshots + asset_snapshots 双表 + 多币种 USD base 重构 + 历史 FX 冻结 + 折线图 | 2026-06-16 | ✅ |
| 图表 | Recharts 折线图（净值走势） | 2026-06-16 | ✅ 部分 |
| 手动刷新 | 持仓页/概览页刷新按钮 + 后端 force_refresh 绕过基金 15min 缓存 | 2026-06-19 | ✅ |
| 概览行情并发+熔断 | overview 行情组并发拉取 + 12s 超时熔断 + 单组容错 + 汇率一次取回 | 2026-06-19 | ✅ |
| 汇率四级兜底 | 内存新鲜→内存过期→运行时缓存→种子文件（data/dbjson/exchange_rates_fallback.json） | 2026-06-19 | ✅ |
| 行情降级兜底 | QuoteStatus 三态 + DB 历史兜底 + QuoteCache 内存缓存层 + 交易时段感知 TTL | 2026-06-19 | ✅ |
| 后台定时预热 | APScheduler 接管数据源，用户请求只读缓存；行情30s + 汇率55min + 启动预热 | 2026-06-20 | ✅ |
| 统一配置类 | SchedulerConfig 集中管理调度间隔/缓存TTL/网络超时，消除散落硬编码 | 2026-06-20 | ✅ |
| 交易为唯一事实源 | 建仓自动生成 buy 交易 + initial_* 删除 + recompute 从 0 起点回放 + 持仓勘误生成交易（为 XIRR 铺路） | 2026-06-20 | ✅ |
| 自定义 CountUp | 轻量 requestAnimationFrame 数字滚动组件替换 react-countup（CJS→ESM 兼容问题） | 2026-07-06 | ✅ |
| 页面入场动画 | 6 个页面统— fade-in + 上滑 500ms 入场动画（概览/持仓/交易/历史交易/行情/历史持仓） | 2026-07-06 | ✅ |
| 动画速度统一 | 卡片/数字/进度条/折线图动画节奏统一到 500-800ms 范围 | 2026-07-06 | ✅ |
| 历史持仓改用 Modified Dietz | 归档时用 Modified Dietz 算盈亏率（建仓=V0，末笔卖出=V1，中间=CF）+ `success` 语义修复 + 前端 `--%` 展示 | 2026-07-07 | ✅ |
| 现金账户管理 | `cash_flows` 资金流水表 + 独立 API + 买卖/建仓自动联动流水 + 前端现金页（入金/出金/流水列表/余额） | 2026-07-27 | ✅ |
| 现金页布局重构 | 左右分栏（左侧 sticky 余额卡片，右侧流水）+ 余额按显示币种换算总额（对齐概览页模式） | 2026-07-28 | ✅ |
| 全系统表格分页 | `PaginatedResponse` 统一分页模型，4 个列表（交易/归档交易/历史持仓/现金流水）接入 `page`/`page_size` + 前端 Pagination 组件 | 2026-07-28 | ✅ |
| 现金语义修复 | `cash_account_enabled` 只决定建仓时资金来源（勾选=余额扣款校验，不勾选=自动入金历史本金），现金追踪永远开 | 2026-07-29 | ✅ |
| 归档连带删流水 | 删除归档持仓时连带删除关联 cash_flows | 2026-07-29 | ✅ |
| 前端质量清理 | tsconfig.app.json 严格检查存量类型错误 + ESLint 清理（react-hooks 严格检查 + react-refresh 混合导出） | 2026-08-02 | ✅ |
| 现金联动闭环修复 | 前端 3 处 mutation 补 cash invalidate（建仓/交易/删归档）→ 操作后现金页立即可见；后端 update_holding 勘误联动流水 + delete_holding 删流水 + create_transaction 金额回退（amount 空时用 qty×price） | 2026-08-04 | ✅ |
| 现金账户测试补齐 | 新增 test_cash_flow_service.py 10 个用例（入金出金/余额换算/建仓联动/勘误联动/删持仓清流水/买卖联动回退） | 2026-08-04 | ✅ |

---

## 二、数据库

| 表 | 行数 | 说明 |
|----|------|------|
| `asset_varieties` | 45,884 | 品种目录 |
| `asset_holdings` | 5 | 当前持仓 |
| `asset_quote` | 20,258 | 行情记录（调度器 30s 预热持续写入） |
| `transactions` | 7 | 交易记录（唯一现金流事实源） |
| `cash_flows` | 30 | 资金流水（deposit/withdraw/buy/sell，买卖自动联动） |
| `closed_holdings` / `closed_transactions` | 0 | 归档持仓 |
| `networth_snapshots` | 7 | 组合级日快照（USD base + fx_rates 冻结） |
| `asset_snapshots` | 0 | 品种级日快照（原币 + USD 双存） |

> 行数统计：2026-08-04 实测。快照为手动记录，每日定时快照见规划 P3。

---

## 三、后端 API 端点

### 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/overview?currency=&force_refresh=` | 概览统计（按 currency 换算，默认 CNY；force_refresh=true 绕过基金缓存强制拉最新） |

### 净值快照

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/snapshots` | 记录今日快照（USD base + 冻结当日 fx_rates） |
| `GET` | `/api/v1/snapshots?currency=&limit=` | 组合级快照列表（按当时汇率换算） |
| `GET` | `/api/v1/snapshots/assets?currency=&ticker=&asset_class=&market=&limit=` | 品种级快照列表 |

### 行情

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/stock/quotes/{CN,US}?codes=` | A 股/美股实时行情 |
| `GET` | `/api/v1/crypto/quotes?coins=` | 加密货币行情 |
| `GET` | `/api/v1/fund/quotes/{CN,US}?codes=` | 基金/ETF 净值 |
| `GET` | `/api/v1/varieties` | 品种目录 |
| `GET` | `/api/v1/varieties/search?q=&limit=` | 品种搜索（ticker/名称模糊匹配） |
| `POST` | `/api/v1/varieties` | 添加品种 |
| `DELETE` | `/api/v1/varieties/{ticker}` | 删除品种（软删除） |

### 持仓

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/holdings` | 持仓列表 |
| `GET` | `/api/v1/holdings/with-quotes?force_refresh=` | 持仓 + 实时行情 + 市值/盈亏/年化（force_refresh=true 绕过基金缓存强制拉最新） |
| `GET` | `/api/v1/holdings/{ticker}` | 单个持仓 |
| `POST` | `/api/v1/holdings` | 新增持仓（名称空时自动补填） |
| `PUT` | `/api/v1/holdings/{ticker}` | 更新持仓 |
| `DELETE` | `/api/v1/holdings/{ticker}` | 删除持仓 |

### 交易

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/transactions?ticker=&page=&page_size=` | 交易列表（分页） |
| `GET` | `/api/v1/transactions/{id}` | 单条交易 |
| `POST` | `/api/v1/transactions` | 新增交易（buy 扣款/sell 入账自动联动现金流水） |
| `PUT` | `/api/v1/transactions/{id}` | 更新交易（联动同步流水金额） |
| `DELETE` | `/api/v1/transactions/{id}` | 删除交易（回退现金流水） |

### 现金账户

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/cash/balances?currency=` | 各币种现金余额 + 按显示币种换算总额（默认 CNY） |
| `GET` | `/api/v1/cash/flows?page=&page_size=` | 资金流水列表（时间倒序，分页） |
| `POST` | `/api/v1/cash/deposit` | 入金（正流水） |
| `POST` | `/api/v1/cash/withdraw` | 出金（负流水，校验同币种余额） |
| `DELETE` | `/api/v1/cash/flows/{flow_id}` | 删除单笔流水 |

> 统一分页：交易/归档交易/历史持仓/现金流水 4 个列表均返回 `PaginatedResponse{data, total, page, page_size}`，`page_size` 默认 20、范围 1-100。

---

## 四、项目文件

→ 详见 [architecture.md](architecture.md)

---

## 五、已知问题 / 技术债

| # | 说明 | 严重度 | 状态 |
|----|------|--------|------|
| 1 | `asset_quote` 表缺少 UNIQUE(ticker, timestamp) 约束 | 中 | ✅ 已修（2026-06-13）<br>ORM 已加约束 + 提供迁移脚本 `backend/script/migrate_asset_quote_unique.py` |
| 2 | `SinaDataSource.close()` 缺少 try/finally | 低 | ✅ 已修（2026-06-13） |
| 3 | ORM `currency` 字段缺默认值 | 低 | ✅ 已修（2026-06-13）<br>`AssetVariety` ORM/Pydantic 均补 `USD` 默认值 |
| 4 | 前端 chunks > 500KB，可按页面 code-split | 低 | ✅ 已修（2026-06-13）<br>路由改 `React.lazy`，最大 chunk 从 >500KB 降至 245KB |

---

## 六、测试覆盖

> 共 150 个 pytest 用例，全通过（测试架构/编写指南见 [docs/testing.md](testing.md)，2026-08-05 报告见 [docs/test_report_2026-08-05.md](test_report_2026-08-05.md)）

| 测试文件 | 用例数 | 覆盖模块 | 关键验证点 |
|---------|--------|---------|-----------|
| `test_transaction_recompute.py` | 8 | `recompute_holding` + `archive_holding` | 基线/买入/卖出/卖超/清仓/归档/白拿股票 |
| `test_asset_holding_service.py` | 10 | `AssetHoldingService` | CRUD + initial_* 基线 + 级联删除 + 三元组行情分发 + 建仓拉行情 + list_all_tickers |
| `test_transaction_service.py` | 10 | `TransactionService` | 校验链 + 事务回滚 + 归档触发 + 修改 ticker 双重重算 |
| `test_exchange_rate.py` | 11 | `exchange_rate.py` | 缓存 TTL + 网络降级 + 内存过期兜底 + 磁盘兜底 + 种子文件回退 + 单飞 + CNY 直通 |
| `test_overview_service.py` | 8 | `OverviewService` | `_calc_annualized` + USD 聚合 + 多币种返回 + 行情并发超时熔断 + 单组异常容错 |
| `test_asset_quote_service.py` | 15 | `AssetQuoteService` | QuoteCache 缓存命中 + force_refresh + DB 历史降级 + 名称补全 + 路由分发 |
| `test_data_sources.py` | 8 | 5 个 `DataSource` | 腾讯解析/前缀/过滤 + CoinGlass JSON + 天天基金 JS 正则 + akshare DataFrame |
| `test_quote_cache.py` | 6 | `QuoteCache` | get/set/过期不丢/部分命中/跨市场隔离/clear |
| `test_trading_hours.py` | 8 | `trading_hours.py` | A股/美股/加密各时段判定 + TTL 兜底 |
| `test_asset_variety_repository.py` | 5 | `AssetVarietyRepository` | 搜索 4 级相关性排序 + limit + 空结果 |
| `test_asset_quote_repository.py` | 4 | `AssetQuoteRepository` | INSERT OR IGNORE 去重 + `get_recent_quotes` 去重/时间窗口 |
| `test_snapshot_service.py` | 6 | `SnapshotService` | 单事务双写 + 多币种聚合 + 当日幂等 + 历史 FX 冻结 + 升序返回 |
| `test_cash_flow_service.py` | 10 | `CashFlowService` + 现金联动 | 入金/出金/余额换算 + 建仓勾选/不勾选 + 勘误 buy/sell + 余额不足拒绝 + 删持仓清流水 + 买卖交易联动/回退 |
| `test_formulas.py` | 18 | `core/formulas.py` 财务公式 | 做T ROI（正/零/负成本 + 脏数据 + 异常）+ 组合聚合（多币种/疯狂做T/兜底）+ XIRR（年化/流水/无解）+ Modified Dietz（权重/同日/零分母） |
| `test_asset_variety_service.py` | 5 | `AssetVarietyService` | 创建/重复冲突/搜索排序/软删除/删不存在 |
| `test_closed_holding_service.py` | 5 | `ClosedHoldingService` | 分页列表/详情含交易/删除连带删流水/删不存在 |
| `test_api_routes.py` | 8 | API 路由层（代表性） | 统一返回格式 + BusinessError/404/422 错误码 + 品种创建搜索 + 现金入金余额 + 交易分页 |
| `test_quote_scheduler.py` | 9 | `QuoteScheduler` | 刷新频率（交易时段/基金/股票间隔）+ 预热写缓存 + 网络失败 DB 兜底 + 汇率 force_refresh |

未覆盖（收益低或需外部环境）：`exceptions.py`、`response.py`、`logger.py`、`scheduler_config.py`（薄层）、SinaDataSource（需 Playwright）、行情 API 端点（依赖真实数据源）、`script/` 导入脚本。详见 [docs/testing.md](testing.md) §5。

---

## 七、后续规划

| 优先级 | 项目 | 说明 |
|--------|------|------|
| P1 | 资产配比饼图 | Recharts PieChart 替代当前进度条 |
| P2 | 多币种切换 UI | 前端加币种切换器，调用 `?currency=USD/HKD/EUR` |
| P3 | 净值快照定时 | 行情+汇率已由 APScheduler 定时预热（30s/55min），剩余：每日自动记录净值快照 |
| P4 | 定投计划 | 周期自动生成交易记录并更新持仓（联动现金扣款） |
| P5 | 汇率源主备切换 | 当前仅 GitHub raw 单一汇率源，加备用源做主备；与磁盘/种子兜底正交 |
