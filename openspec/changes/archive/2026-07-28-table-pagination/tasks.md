## 1. 后端分页基础设施

- [x] 1.1 新增 `app/models/common.py`：`PaginatedResponse[T]` 泛型模型
- [x] 1.2 新增 `app/core/response.py` 的 `success_paginated` 辅助（或在 api 层直接构造）

## 2. 后端接口改造（4 个）

- [x] 2.1 `transaction_api` + `transaction_repository`：`list_transactions(page, page_size)` 返回分页
- [x] 2.2 `cash_flow_api` + `cash_flow_repository`：`list_flows(page, page_size)` 返回分页
- [x] 2.3 `closed_holding_api` + `closed_holding_repository`：`list_closed_transactions(page, page_size)` 返回分页
- [x] 2.4 `closed_holding_repository`：`list_closed_holdings(page, page_size)` 返回分页

## 3. 前端分页组件

- [x] 3.1 新增 `components/ui/pagination.tsx`：`<Pagination page pageSize total onPageChange onPageSizeChange />`
- [x] 3.2 页码超过 7 页时中间省略

## 4. 前端 hooks + 类型

- [x] 4.1 `types/index.ts` 加 `PaginatedResponse<T>` 类型
- [x] 4.2 `api/endpoints.ts`：4 个 fetch 函数改为 `(page, pageSize)` 参数，返回 `PaginatedResponse`
- [x] 4.3 hooks：`useTransactions`/`useCashFlows`/`useClosedTransactions`/`useClosedHoldings` 支持 page/pageSize 作为 queryKey

## 5. 前端页面接入

- [x] 5.1 `TransactionsPage` 表格下加 `<Pagination>`
- [x] 5.2 `CashPage` 流水表下加 `<Pagination>`
- [x] 5.3 `ClosedTransactionsPage` 表格下加 `<Pagination>`
- [x] 5.4 `HistoryPage` 表格下加 `<Pagination>`

## 6. 验证

- [x] 6.1 后端 pytest 更新分页断言 + 无回归
- [x] 6.2 前端 tsc 通过
