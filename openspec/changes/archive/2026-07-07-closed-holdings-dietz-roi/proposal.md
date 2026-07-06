## Why

历史持仓（已清仓）的盈亏率当前在前端用 `realized_pnl / total_buy_amount` 计算，做T操作会拉低盈利率，且与 active holdings 的计算口径不一致。改用 Modified Dietz 计算，使结果不受做T干扰、与持仓盈亏率语义对齐。

## What Changes

- 归档时用 `calculate_modified_dietz(V0=0, V1=0, trade_flows=t∈该周期交易)` 计算盈亏率，结果存入 `closed_holdings` 表
- `ClosedHolding` Pydantic 模型新增 `pnl_pct`（百分比）和 `is_crazy_trader`（是否零成本/负成本持有）字段
- 前端历史持仓列表和详情弹窗从 API 字段读取盈亏率，删除 inline 除法计算
- 当 `is_crazy_trader=True` 时，前端显示 `--%`（不显示 N/A 或 "+∞%"）

## Capabilities

### New Capabilities
- `closed-holding-dietz-return`: 已清仓持仓的 Modified Dietz 收益率计算，含归档时算、存储、前端展示

### Modified Capabilities

（无现有 specs 需要修改）

## Impact

- **backend/app/core/formulas.py**: `calculate_modified_dietz` 已修复 `success` 语义，无需额外修改
- **backend/app/services/asset_holding_service.py**: `archive_holding()` 新增 Modified Dietz 计算逻辑
- **backend/app/models/orm/closed_holding_orm.py**: `ClosedHoldingRecord` 加 2 列（`pnl_pct`, `is_crazy_trader`）
- **backend/app/models/closed_holding.py**: `ClosedHolding` 加对应字段
- **backend/app/repositories/closed_holding_repository.py**: `_record_to_closed_holding()` 追加映射
- **frontend/src/features/history/HistoryPage.tsx**: 删 `pnlPct()` inline 计算，读 API 字段，`--%` 展示
- **frontend/src/features/history/ClosedHoldingDetailDialog.tsx**: 同删 inline 计算
