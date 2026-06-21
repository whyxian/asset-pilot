# 计算公式清单

> 最后更新：2026-06-21
> 记录系统中所有收益计算相关公式及其代码位置，便于后续统一管理和 XIRR 迁移。

---

## 一、单只持仓（实时）

代码位置：`backend/app/services/asset_holding_service.py`

| 公式 | 代码行 | 说明 |
|------|--------|------|
| `市值 = 数量 × 现价` | `_build_holding_with_quote:319` | |
| `盈亏金额 = 市值 - 总投入` | `_build_holding_with_quote:320` | |
| `盈亏率 = (现价 - 成本) / 成本 × 100%` | `_build_holding_with_quote:324` | **成本 > 0 时** |
| `盈亏率 = (现价 - 成本) / 首买价 × 100%` | `_build_holding_with_quote:326` | **成本 ≤ 0 时**（剩余底仓收益率） |
| 年化回报 | `_build_holding_with_quote:329` | 暂不计算（`None`），待 XIRR 落地 |

## 二、成本价重算（recompute）

代码位置：`backend/app/services/asset_holding_service.py`

| 公式 | 代码行 | 说明 |
|------|--------|------|
| **buy 回放**: `q += qty, t += amt` | `recompute_holding:420-422` | 从 0 起点累加。`amt` 优先取 `amount`，其次 `quantity × unit_price` |
| **sell 回放**: `q -= qty, t -= sell_price × qty` | `recompute_holding:442-443` | 降低成本法。`sell_price` 优先 `unit_price`，其次 `amount / qty`，兜底当前 `cost_price` |
| `成本价 = t / q` | `recompute_holding:422` | 可正可负可为 0（允许负成本） |
| 成本下限 | `recompute_holding:445-446` | 已删除（原 `if t < 0: t = 0`），现允许负成本 |

## 三、快照记录（单只）

代码位置：`backend/app/services/snapshot_service.py`

| 公式 | 代码行 | 说明 |
|------|--------|------|
| `市值 = 数量 × 现价` | `snapshot_service:66` | |
| `未实现盈亏 = 市值 - 总投入` | `snapshot_service:67` | |
| `return_pct = (现价-成本) / 成本 × 100%` | `snapshot_service:79` | 成本 > 0 |
| `return_pct = (现价-成本) / 首买价 × 100%` | `snapshot_service:81` | 成本 ≤ 0 |
| 年化回报 | `snapshot_service:84` | 暂不计算（`None`） |

> ⚠️ `first_buy_price` 未存入 asset_snapshots 表——历史快照无法用新公式重算 return_pct。

## 四、历史持仓（已清仓归档）

代码位置：`backend/app/services/asset_holding_service.py`

| 公式 | 代码行 | 说明 |
|------|--------|------|
| `已实现盈亏 = sum_sell - sum_buy` | `archive_holding:524` | 全部 sell 金额 - 全部 buy 金额（建仓 buy 已含在内） |
| `总买入金额 = sum_buy` | `archive_holding:543` | 存入 `closed_holding.total_buy_amount` |

前端显示（两处相同公式）：

| 公式 | 代码位置 |
|------|---------|
| `盈亏率 = realized_pnl / total_buy_amount × 100%` | `HistoryPage.tsx:25-28`（`pnlPct` 函数） |
| `盈亏率 = realized_pnl / total_buy_amount × 100%` | `ClosedHoldingDetailDialog.tsx:81`（内联） |

## 五、组合概览

代码位置：`backend/app/core/formulas.py` → `calculate_portfolio_overview`

| 公式 | 说明 |
|------|------|
| `单只市值 = 持仓股数 × 当前股价` | 内部逐只计算 |
| `单只成本 = 持仓股数 × 券商成本价` | 内部逐只计算 |
| `单只市值(USD) = 单只市值 / 汇率[currency]` | 内部汇率换算 |
| `单只成本(USD) = 单只成本 / 汇率[currency]` | 内部汇率换算 |
| `总市值(USD) = Σ 单只市值(USD)` | 内部累加 |
| `总成本(USD) = Σ 单只成本(USD)` | 内部累加 |
| `总盈亏 = 总市值 - 总成本` | |
| `总盈亏率 = 总盈亏 / 总成本 × 100%` | 总成本≤0 且市值>0 时返回 `None`（前端显示 `+∞%`） |
| 组合年化 | 暂不计算（`None`） |

调用方：`overview_service.py` + `snapshot_service.py`（传原始逐只数据 + rates，公式内部完成全部数学运算）

## 六、快照汇总（组合级）

代码位置：`backend/app/services/snapshot_service.py`

| 公式 | 代码行 | 说明 |
|------|--------|------|
| `总市值(USD) = Σ(个股市值 × 汇率)` | `snapshot_service:69-72` | |
| `总成本(USD) = Σ(个股总投入 × 汇率)` | `snapshot_service:70` | |
| `总盈亏 = 总市值 - 总成本` | `snapshot_service:105` | |
| `配比 = 该市场市值 / 总市值 × 100%` | `snapshot_service:119` | |

## 七、前端表单录入联动

代码位置：`frontend/src/features/holdings/HoldingFormDialog.tsx`

| 输入 | 自动算出 | 代码行 |
|------|---------|--------|
| 数量 + 成本价 | `总投入 = qty × price` | `:171` |
| 成本价 + 总投入 | `数量 = total ÷ price` | `:177` |
| 数量 + 总投入 | `成本价 = total ÷ qty` | `:180` |

---

## 重复公式清单

以下公式在多处出现相同的计算逻辑，后续修改需同步：

| 公式 | 位置 1 | 位置 2 |
|------|--------|--------|
| 盈亏率（成本>0） | `asset_holding_service:324` | `snapshot_service:79` |
| 盈亏率（成本≤0） | `asset_holding_service:326` | `snapshot_service:81` |
| 历史盈亏率 | `HistoryPage:25-28` | `ClosedHoldingDetailDialog:81` |
| 市值 = 数量 × 现价 | `asset_holding_service:319` | `snapshot_service:66` |

> 待后续统一抽取到公共函数，避免改公式时遗漏。
