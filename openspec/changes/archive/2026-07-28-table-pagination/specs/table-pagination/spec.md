## ADDED Requirements

### Requirement: 列表接口支持分页

所有列表接口 SHALL 接受 `page`（默认 1）和 `page_size`（默认 20，上限 100）参数，返回 `PaginatedResponse` 结构（含 data/total/page/page_size）。

#### Scenario: 默认分页

- **WHEN** 调用 `GET /api/v1/transactions`（不带参数）
- **THEN** 返回第 1 页，page_size=20，total 为总记录数

#### Scenario: 指定页码和每页条数

- **WHEN** 调用 `GET /api/v1/transactions?page=3&page_size=50`
- **THEN** 返回第 3 页 50 条数据，total 反映全部记录数

### Requirement: 前端分页组件

系统 SHALL 提供共享 `<Pagination>` 组件，含页码导航、上一页/下一页、每页条数选择器（20/50/100）、总条数显示。

#### Scenario: 翻页

- **WHEN** 用户点击页码 2
- **THEN** 表格刷新显示第 2 页数据

#### Scenario: 切换每页条数

- **WHEN** 用户将每页条数从 20 改为 50
- **THEN** 页码重置到第 1 页，按 50 条/页重新加载
