# 自选股 + 行情页改版

## Why

当前行情页只有「输入代码 → 单张结果卡片」，功能单一且布局大量留白：卡片是横向窄条（max-w-md），其余区域全空。用户无法收藏常看的标的，行情也不会自动刷新——每次查询都是手动触发的一次性操作。

## What Changes

- **新增自选股能力（watchlist）**：
  - 后端新增 `watchlist` 表 + 4 个 API：列表 / with-quotes（带行情+QuoteStatus 三态）/ 收藏 / 取消收藏
  - 收藏时若 `(asset_class, market, ticker)` 品种不存在于 `asset_varieties`，同一事务内自动注册（复用品种创建逻辑）；重复收藏幂等返回已有记录
  - 取消收藏仅移除自选，不影响品种库
  - 表预留 `sort_order` 字段（默认 0，后续手动排序免迁移）
- **行情页布局改版**：
  - 顶部搜索栏（输入 + 市场下拉 + 查询按钮）不变
  - 中部为**自选区网格**（响应式多列占满宽度），卡片含：名称/代码/现价/涨跌（红绿）/行情状态标记（REALTIME/HISTORICAL/UNAVAILABLE）/♥ 取消收藏
  - 空自选态显示引导文案「查询后点击 ♥ 收藏」
  - 查询结果改为**弹窗**展示（含 ♥ 收藏 + 显式「添加到品种库」按钮）
  - 点击自选卡片也弹出详情弹窗（复用查询结果弹窗组件）
  - 自选行情 **30s 轮询**（对齐持仓页 `POLL_INTERVAL` 模式，读后端缓存零成本）
- **交互**：收藏/取消收藏采用**乐观更新**（点击即时反馈，失败回滚）
- **币种**：自选卡片按各自原币显示（持仓页模式），不做汇率换算

## Capabilities

- **New Capabilities**:
  - `watchlist` — 自选股管理：收藏/取消/列表/带行情刷新

- **Modified Capabilities**: 无（现有 spec 均不涉及；行情查询行为不变，仅布局与入口变化）

## Impact

| 范围 | 影响 |
|------|------|
| 后端 | 新增 `app/models/orm/asset_watchlist_orm.py`、`app/models/asset_watchlist.py`、`app/repositories/watchlist_repository.py`、`app/services/watchlist_service.py`、`app/api/watchlist_api.py`；复用 `AssetQuoteService.fetch_quotes_by_asset_class` + QuoteCache/QuoteStatus；`init_db` 自动建新表（无需迁移） |
| 前端 | 新增 `useWatchlist` hook（30s 轮询 + 乐观更新 mutations）、`WatchlistGrid`（自选区）、`QuoteDialog`（结果/详情弹窗）；改版 `QuotesPage`（搜索栏 + 自选区）；`endpoints.ts`/`types` 补 watchlist 端点 |
| 测试 | 后端：`test_watchlist_service.py`（收藏幂等/自动注册品种/取消/with-quotes 三态）+ API 路由测试；前端 tsc/eslint |
| 数据库 | 新表 `watchlist`（审计字段齐全），`asset_varieties` 可能被自动注册写入（复用现有品种创建约束） |

已知限制：注册品种的分类以查询时下拉选择的 `asset_class/market` 为准（如 SHIB 需手动切加密货币再查询收藏），错误时用户重新查询再收藏即可覆盖；收藏入口只在查询成功弹窗出现，不存在的结果不会入库（查无结果已抛 40002）。
