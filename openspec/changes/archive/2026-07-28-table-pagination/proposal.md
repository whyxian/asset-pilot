## Why

系统所有列表表格（交易、资金流水、归档交易、归档持仓）都没有分页，只靠 `limit` 取前 N 条，超出部分用户永远看不到。用久了交易/流水累计上千条后，历史记录直接丢失不可见。

## What Changes

- 后端列表接口统一改为分页：`?page=1&page_size=20`，返回 `{data, total, page, page_size}`
- 新增共享 `PaginatedResponse[T]` 模型
- 前端新增共享 `<Pagination>` 组件（页码 + 上一页/下一页 + 每页条数选择器）
- 4 个表格接入分页：交易记录、资金流水、归档交易、归档持仓
- 不动：净值快照（图表数据，按日期范围加载）、品种搜索（搜索结果）

## Capabilities

### New Capabilities
- `table-pagination`: 列表分页能力（后端分页响应 + 前端分页组件）

### Modified Capabilities

（无现有 specs 需要修改）

## Impact

- **Backend**: 新增 `PaginatedResponse` 模型；4 个 list 接口改为分页查询（COUNT + LIMIT OFFSET）
- **Frontend**: 新增 `<Pagination>` 组件；4 个页面表格接入；hooks 支持分页参数
- 默认 page_size=20，前端可选 20/50/100
