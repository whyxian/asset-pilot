# 自选股 + 行情页改版 — 设计

## Context

行情页现状：`useMutation` 一次性查询 + 单张窄卡片 + 大量空白。项目已有成熟基建：
- 行情链路：`QuoteCache 内存缓存（进程级单例）→ DB 历史兜底 → QuoteStatus 三态`，调度器 30s 预热，**用户请求只读缓存**
- 轮询模式：持仓/概览页 `refetchInterval: POLL_INTERVAL (30s)`（`useHoldings` / `useOverview`）
- 乐观更新先例：持仓页刷新 `setQueryData`
- 品种注册：`POST /api/v1/varieties` + `AssetVarietyRepository.create_variety`（唯一约束 `(asset_class, market, ticker)`）
- 错误码已统一管理（`error_codes.py`），新接口抛错必须用常量

## Goals / Non-Goals

**Goals**
- 后端 watchlist 完整 CRUD + with-quotes 三态行情，收藏自动注册品种（事务原子）
- 前端行情页：自选区网格占满宽度 + 查询结果弹窗 + 30s 轮询 + 乐观更新
- 全链路测试（service/repo/API）

**Non-Goals**
- 手动排序 UI（表预留 sort_order，本轮不做交互）
- 行情页手动 force_refresh 按钮（30s 轮询已覆盖，后续迭代）
- 自选按显示币种换算（原币显示）
- 多代码批量查询/批量收藏

## Decisions

### D1: watchlist 表结构（预留排序）

```
watchlist
  id            INTEGER PK AUTOINCREMENT
  ticker        VARCHAR(30)  NOT NULL
  asset_class   VARCHAR(10)  NOT NULL
  market        VARCHAR(10)  NOT NULL
  name          VARCHAR(200) NOT NULL DEFAULT ''   -- 收藏时快照，避免回查品种
  sort_order    INTEGER      NOT NULL DEFAULT 0    -- 预留手动排序（本轮不用）
  created_at / updated_at / created_by / updated_by  -- 审计字段（强制）
约束：UNIQUE(asset_class, market, ticker)
索引：ix_watchlist_ticker ON (ticker)
```

- **为什么不用 FK → asset_varieties**：自选允许收藏品种表之外的代码（查询成功即可收藏），FK 会锁死；名称在收藏时快照，不依赖品种表存在
- **为什么预留 sort_order**：排序功能后续迭代时无需迁移（SQLite 加列成本高）

### D2: 收藏 = 隐式注册品种（一个事务）

`POST /api/v1/watchlist` 流程：
1. 查 `asset_varieties` 是否存在 `(asset_class, market, ticker)`（`AssetVarietyRepository.get_variety`）
2. 不存在 → 同事务 `create_variety`（复用现有 repo，含唯一约束冲突兜底）
3. 写 watchlist（重复收藏 → 幂等返回已有记录，不报错）

- **为什么不拉行情校验**：收藏入口只在查询成功弹窗出现（查无结果已抛 40002），流程保证"不存在的结果不会入库"；收藏保持零网络延迟（乐观更新配合）
- **备选**（未采纳）：收藏时复用建仓的行情校验——增加收藏延迟且停牌/退市标的无法收藏，过重

### D3: with-quotes 端点复用行情三态链路

`GET /api/v1/watchlist/with-quotes`：拉全部自选 → 按 `(asset_class, market)` 分组 → 调 `AssetQuoteService.fetch_quotes_by_asset_class`（内部 QuoteCache → DB 历史 → UNAVAILABLE 三态，与持仓页 `holdings/with-quotes` 同链路）→ 合并返回 `[{...watchlist 字段, quote, status}]`。

前端 `useWatchlist` 30s `refetchInterval` 轮询此端点，读后端缓存零成本（对齐持仓页模式）。

### D4: 乐观更新

取消/收藏收藏用 TanStack Query `onMutate` 乐观更新：
- 收藏：立即把新项写入 `watchlist` query 缓存（本地构造占位，含前端已拿到的 quote/name）→ 请求失败回滚 + toast
- 取消：立即从缓存移除 → 失败回滚 + toast
- 与持仓页刷新 `setQueryData` 同模式；mutation 成功后 invalidate `['watchlist']` 对齐服务端真实数据

### D5: 布局与交互（方案 1 + 查询弹窗）

```
┌──────────────────────────────────────────────┐
│ 行情 [输入框] [下拉] [查询]                    │
├──────────────────────────────────────────────┤
│ 自选区（grid-cols-2/3/4 响应式）              │
│ ┌────────┐ ┌────────┐ ┌────────┐             │
│ │名称/代码 │ │现价/涨跌 │ │♥ 状态标记 │ ...      │
│ └────────┘ └────────┘ └────────┘             │
│ 空态：引导卡片「查询后点击 ♥ 收藏」            │
└──────────────────────────────────────────────┘
查询 → Dialog：结果卡片 + [♥ 收藏(乐观)] + [添加到品种库]
点自选卡片 → 同一 Dialog 组件（详情模式）
```

- **为什么弹窗**：用户选定——查询结果不占页面空间，自选区常驻；页面主体永远是自选行情（进来看自选，搜了看结果）
- **弹窗复用**：查询结果与卡片详情共用 `QuoteDialog`（props 区分 mode），保持单一组件

### D6: 状态标记与币种

- 自选卡片复用持仓页模式：`HISTORICAL` 追加"历史"小字、`UNAVAILABLE` 显示"—"
- 原币显示（`quote.currency`），不做汇率换算

## Risks / Trade-offs

- **[风险] 品种分类准确性依赖查询下拉选择**（SHIB 不在硬编码符号表会被识别为美股）→ 弹窗收藏时显示当前分类，用户可改下拉后重新查询；错误注册对自选显示无影响（行情照样显示）；后续可单独做加密符号识别改进。**本轮接受该限制**
- **[风险] 乐观更新与服务端状态不一致**（收藏失败回滚）→ onMutate 快照 + onError 回滚 + toast 提示；invalidate 兜底最终一致
- **[风险] 自动注册品种可能引入脏数据**（用户收藏不存在的代码，前端流程已挡）→ 后端不额外校验（见 D2），若后续发现恶意/异常写入再加校验
- **[风险] watchlist 无 FK，手动删品种后自选悬空** → 自选卡片靠行情端点拉取（不依赖品种表），name 为快照，可正常展示；删除自选即可清理

## Migration Plan

- 新表由 `init_db` 的 `create_all` 自动创建（SQLite 无迁移框架，create_all 只建缺失表），**无需迁移脚本、无需备份**
- 部署顺序：后端先行（watchlist API 与旧前端无冲突）→ 前端改版 → 测试全绿
- 回滚：前端改版回滚即恢复旧页（新 API 无害留存）；后端回滚删表即可（自选数据丢失可接受，无其他依赖）

## Open Questions

- 无（探索阶段已与用户逐项确认：存储后端表 / 布局上下+弹窗 / 30s 轮询 / 乐观更新 / 状态标记 / 原币显示 / 命名 watchlist_xxx.py）
