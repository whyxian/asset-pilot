## Context

4 个列表表格（交易/资金流水/归档交易/归档持仓）当前只取前 N 条，无分页。统一改为 offset 分页。

## 后端设计

### 共享分页响应模型

```python
# app/models/common.py
class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    page_size: int
```

### 接口改造

所有 list 接口统一参数：`page: int = Query(1, ge=1)`, `page_size: int = Query(20, ge=1, le=100)`

查询模式（每个 repo 加一个分页方法）：
```python
# COUNT 拿总数
total = await session.scalar(select(func.count()).select_from(Model))
# LIMIT OFFSET 拿当前页
records = await session.execute(
    select(Model).order_by(...).limit(page_size).offset((page - 1) * page_size)
)
```

返回 `PaginatedResponse(data=..., total=total, page=page, page_size=page_size)`

### 改造范围

| 接口 | 排序 |
|------|------|
| `GET /api/v1/transactions` | transaction_date DESC, id DESC |
| `GET /api/v1/cash/flows` | created_at DESC, id DESC |
| `GET /api/v1/closed-transactions` | transaction_date DESC, id DESC |
| `GET /api/v1/closed-holdings` | closed_at DESC, id DESC |

保留 `limit` 参数做向后兼容？**不保留**，直接改为 `page`/`page_size`（前端一并改，无外部消费者）。

## 前端设计

### 共享 `<Pagination>` 组件

```
┌──────────────────────────────────────────────┐
│  共 234 条  [20条/页 ▼]  ← 1 2 3 ... 12 →   │
└──────────────────────────────────────────────┘
```

Props: `{ page, pageSize, total, onPageChange, onPageSizeChange }`

- 页码超过 7 页时中间省略（1 2 3 ... 10 11 12）
- 每页条数选择器：20 / 50 / 100
- 总条数显示

### hooks 改造

```typescript
// useTransactions(page, pageSize) -> { data, total, ... }
// 把 page/pageSize 作为 queryKey 一部分，切换页码自动重新请求
```

### 页面改造

4 个页面的表格下方放 `<Pagination>`，state 管理 `page`/`pageSize`，切换时重置 page=1。

## 风险 / 取舍

- **性能**：`OFFSET` 在大表上会越来越慢（需扫描 offset+limit 行）。个人投资场景数据量小（千级），可接受。真到万级再上 cursor 分页。
- **COUNT 开销**：每次查询多一次 COUNT。SQLite 上千级数据无压力。
