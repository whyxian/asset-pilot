## 1. DB Schema

- [x] 1.1 创建 `cash_flows` 表 ORM（CashFlowRecord，字段：id/type/amount/currency/transaction_id/notes/审计字段）
- [x] 1.2 `asset_holdings` ORM 加 `cash_account_enabled` 列（Boolean, default false）
- [x] 1.3 `init_db()` 加 ALTER TABLE 迁移

## 2. 后端新层：CashFlow

- [x] 2.1 CashFlow Pydantic 模型（CashFlow 响应 + CreateDeposit/CreateWithdraw 请求）
- [x] 2.2 CashFlowRepository（create / list / delete / sum_by_currency）
- [x] 2.3 CashFlowService（入金/出金/查询余额/查询流水）
- [x] 2.4 CashFlow API 路由（GET /balances, GET /flows, POST /deposit, POST /withdraw, DELETE /flows/{id}）
- [x] 2.5 注册路由到 app/main.py

## 3. TransactionService 联动

- [x] 3.1 `create_transaction`：buy 时校验现金余额 + 写 type=buy cash_flow；sell 时写 type=sell cash_flow
- [x] 3.2 `update_transaction`：同步更新关联 cash_flow 的 amount
- [x] 3.3 `delete_transaction`：删除关联 cash_flow

## 4. 建仓支持 cash_account_enabled

- [x] 4.1 `AssetHoldingCreate` Pydantic 加 `cash_account_enabled: bool = False`
- [x] 4.2 `AssetHoldingService.create_holding` 写入 `cash_account_enabled`
- [x] 4.3 `AssetHoldingService.update_holding` 忽略该字段（不可改）

## 5. 前端现金页面

- [x] 5.1 现金路由 + 侧边栏菜单项
- [x] 5.2 余额卡片组件（分币种 + 总资产）
- [x] 5.3 流水列表组件（时间倒序，类型/金额/备注）
- [x] 5.4 入金/出金弹窗

## 6. 前端建仓钩子

- [x] 6.1 建仓对话框加"从现金账户扣除"勾选框
- [x] 6.2 持仓页 API 调用同步 `cash_account_enabled` 参数

## 7. 验证

- [x] 7.1 pytest 新用例覆盖 cash_flow CRUD 和联动逻辑
- [x] 7.2 现有 95 个用例无回归
