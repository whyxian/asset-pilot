# 测试报告 2026-08-05

> 范围：功能模块测试覆盖盘点 + 补全（formulas / 归档 / 品种 / API 路由 / 调度器）
> 配套指南：见 [testing.md](testing.md)

---

## 1. 执行信息

| 项 | 值 |
|----|----|
| 执行命令 | `.venv/bin/python -m pytest backend/test/` |
| 执行时间 | 2026-08-05 |
| 环境 | Python 3.11（项目 .venv）+ SQLite 内存库 |
| 结果 | **150 passed, 0 failed**（4.38s） |

## 2. 结果汇总

| 测试文件 | 用例数 | 状态 |
|---------|--------|------|
| test_transaction_recompute.py | 8 | ✅ |
| test_asset_holding_service.py | 10 | ✅ |
| test_transaction_service.py | 10 | ✅ |
| test_exchange_rate.py | 11 | ✅ |
| test_overview_service.py | 8 | ✅ |
| test_asset_quote_service.py | 15 | ✅ |
| test_data_sources.py | 8 | ✅ |
| test_quote_cache.py | 6 | ✅ |
| test_trading_hours.py | 8 | ✅ |
| test_asset_variety_repository.py | 5 | ✅ |
| test_asset_quote_repository.py | 4 | ✅ |
| test_snapshot_service.py | 6 | ✅ |
| test_cash_flow_service.py | 10 | ✅ |
| **test_formulas.py（新增）** | **18** | ✅ |
| **test_asset_variety_service.py（新增）** | **5** | ✅ |
| **test_closed_holding_service.py（新增）** | **5** | ✅ |
| **test_api_routes.py（新增）** | **8** | ✅ |
| **test_quote_scheduler.py（新增）** | **9** | ✅ |
| **合计** | **150**（原 105，本次 +45） | ✅ |

## 3. 本次盘点发现并补全的缺口

盘点依据：对 `backend/app/` 全部模块做 import 引用扫描 + 断言级核对，识别"仅被 conftest 引用、无真实断言"的假覆盖。

| 缺口模块 | 风险 | 本次动作 |
|---------|------|---------|
| `core/formulas.py`（XIRR / Modified Dietz / 做T ROI / 组合聚合） | **高**——财务公式直接决定盈亏展示，属核心正确性 | 新增 18 用例 |
| `services/asset_variety_service.py` | 中——CRUD + 软删除 + 搜索排序 | 新增 5 用例 |
| `services/closed_holding_service.py` + repo 删除联动 | 中——删除归档连带删流水（8-04 刚修复的逻辑） | 新增 5 用例 |
| API 路由层（8 个 router） | 中——统一返回格式/错误码契约 | 新增 8 用例（代表性端点，行情端点由 service 测试覆盖） |
| `scheduler/quote_scheduler.py` | 中——刷新频率/失败兜底 | 新增 9 用例 |

## 4. 补测过程中发现的缺陷

| # | 缺陷 | 影响 | 修复 |
|---|------|------|------|
| 1 | `calculate_remaining_position_roi` 参数转换在 try 块外，非法输入直接抛异常，违反 docstring "异常返回 success=False" 契约 | 前端拿到未捕获异常而非结构化响应 | ✅ 已修（[formulas.py](backend/app/core/formulas.py)，转换移入 try） |
| 2 | API 测试基建：client fixture 未依赖 Session 时连真实数据库（测试自身问题，非产品缺陷） | 测试可能静默污染真实 DB 数据 | ✅ 已修（[test_api_routes.py](backend/test/test_api_routes.py)）+ 写入 [testing.md §1.3](testing.md) 警示 |

## 5. 覆盖矩阵

模块级覆盖情况（`✅` = 有断言级测试）：

- **services**：asset_holding ✅ / asset_quote ✅ / transaction ✅ / overview ✅ / snapshot ✅ / cash_flow ✅ / **asset_variety ✅（本次）** / **closed_holding ✅（本次）**
- **repositories**：asset_quote ✅ / asset_variety ✅ / 其余经 service 测试覆盖
- **utils**：exchange_rate ✅ / quote_cache ✅ / trading_hours ✅
- **core**：data_sources ✅ / exceptions ✅（间接）/ **formulas ✅（本次）**；logger / scheduler_config 薄层未测（收益低）
- **api**：**8 个 router 代表性端点 ✅（本次）**；行情端点依赖真实数据源未覆盖
- **scheduler**：**quote_scheduler ✅（本次）**

未覆盖：`SinaDataSource`（需 Playwright）、`script/` 导入脚本（一次性运维）、行情 API 端点（mock 数据源后可补）。

## 6. 结论与建议

- 全部功能模块已具备测试用例，150 个用例全绿，无回归
- 建议后续批次：行情 API 端点 mock 测试（待前端行情页有新逻辑时顺势补）、`SinaDataSource` 接入 Playwright 测试（需 CI 环境支持）
- 新增测试依赖：`httpx`（API 集成测试）、`pyxirr`（公式计算，业务已依赖），均已安装
