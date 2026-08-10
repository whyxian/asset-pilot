# 实施任务清单

## 1. 后端：watchlist 数据层

- [x] 1.1 新建 `app/models/orm/asset_watchlist_orm.py` — `WatchlistRecord`（ticker/asset_class/market/name/sort_order + 审计字段，UNIQUE(asset_class, market, ticker)）
- [x] 1.2 新建 `app/models/asset_watchlist.py` — `WatchlistItem` / `WatchlistWithQuote` / `WatchlistCreate`（Pydantic）
- [x] 1.3 新建 `app/repositories/watchlist_repository.py` — `WatchlistRepository`：`list_watchlist`（sort_order, id 倒序）/ `get_watchlist` / `create_watchlist` / `delete_watchlist`（幂等删除）
- [x] 1.4 conftest.py patch 列表补 `watchlist_repository` / `watchlist_service`

## 2. 后端：watchlist 服务与 API

- [x] 2.1 新建 `app/services/watchlist_service.py` — `WatchlistService`：
  - `create_watchlist`：事务内「品种不存在 → 自动注册（复用 AssetVarietyRepository.create_variety）→ 写 watchlist；已存在 → 幂等返回已有」
  - `list_with_quotes`：按 (asset_class, market) 分组调 `AssetQuoteService.fetch_quotes_by_asset_class`，合并 QuoteStatus 三态
- [x] 2.2 新建 `app/api/watchlist_api.py` — 4 个端点：
  - `GET /api/v1/watchlist` 列表
  - `GET /api/v1/watchlist/with-quotes` 自选 + 行情三态
  - `POST /api/v1/watchlist` 收藏（含自动注册）
  - `DELETE /api/v1/watchlist/{id}` 取消收藏
- [x] 2.3 `main.py` 注册 watchlist_router
- [x] 2.4 错误码：新增场景（如有）用 `error_codes.py` 常量，不新增硬编码

## 3. 后端：测试

- [x] 3.1 新建 `test_watchlist_service.py`：收藏成功（含自动注册品种）/ 重复收藏幂等 / 取消收藏不影响品种库 / with-quotes 三态（mock 行情链路）/ 列表倒序
- [x] 3.2 `test_api_routes.py` 补 watchlist 端点：POST 收藏 → GET 列表 → DELETE 取消
- [x] 3.3 全套 pytest 通过

## 4. 前端：数据层

- [x] 4.1 `endpoints.ts` 补 watchlist 4 个端点函数 + `types` 补 `WatchlistItem` / `WatchlistWithQuote`
- [x] 4.2 新建 `useWatchlist.ts`：
  - `useWatchlistQuotes()` — `['watchlist','with-quotes']` + `refetchInterval: POLL_INTERVAL (30s)`
  - `useAddWatchlist()` / `useRemoveWatchlist()` — 乐观更新（onMutate 快照 + 回滚）+ 成功后 invalidate
  - `useAddVariety()` — 显式添加到品种库（复用现有 varieties API）+ 本地状态"已注册"

## 5. 前端：行情页改版

- [x] 5.1 新建 `WatchlistGrid` 组件：响应式网格（grid-cols-2/3/4），卡片 = 名称/代码/现价/涨跌幅（红绿）/状态标记（HISTORICAL 小字、UNAVAILABLE —）/♥ 取消（乐观更新）；空态引导文案
- [x] 5.2 新建 `QuoteDialog` 组件：查询结果 + 卡片详情共用；含 ♥ 收藏（乐观更新、已收藏态）+ 「添加到品种库」按钮（已注册态）
- [x] 5.3 改版 `QuotesPage`：搜索栏（保留现有 detectMarket 自动识别）+ 自选区（WatchlistGrid 常驻主体）+ 查询触发 QuoteDialog；移除页内结果卡片区与旧空态
- [x] 5.4 弹窗/收藏成功后 invalidate `['watchlist']`，自选区即时更新

## 6. 前端：验证与收尾

- [x] 6.1 `tsc -b` + `eslint` 通过
- [x] 6.2 手动验证：查询 → 收藏（自选出现）→ 30s 轮询刷新 → 取消收藏 → 添加到品种库（品种搜索可命中）
- [x] 6.3 更新 `docs/progress.md`（完成表 + API 端点 + DB 表统计）与 `docs/testing.md`（覆盖矩阵）
