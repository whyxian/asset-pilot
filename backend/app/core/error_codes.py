"""统一错误码定义 — 系统所有错误码集中管理

所有 BusinessError 的 code 必须引用这里的常量，禁止散落硬编码。
新增业务错误场景时：先在此处确认/新增码值，再使用常量。

编码结构：
- 0      成功
- 4xxxx  业务错误（BusinessError → HTTP 200 + {code, message, data}）
- 4xx    框架层 HTTP 错误（不走 BusinessError，供前端/文档对照）
"""

# ── 成功 ──
CODE_SUCCESS = 0  # 统一成功码（ApiResponse 默认，success() 返回）

# ── 业务错误（BusinessError → HTTP 200 + {code, message, data}）──
CODE_VALIDATION = 40001  # 业务校验失败：未识别品种代码 / 现金余额不足 / 费率超范围 / 不支持的数据源 / 归档前提不满足
CODE_QUOTE_UNAVAILABLE = 40002  # 行情不可用：数据源查无此代码（建仓拉行情失败 / 行情查询查无结果）
CODE_NOT_FOUND = 40401  # 资源不存在：持仓 / 交易 / 品种 / 归档持仓 / 资金流水

# ── 框架层错误（不由 BusinessError 抛出，供前端/文档对照）──
CODE_HTTP_404 = 404  # 路由不存在（StarletteHTTPException handler）
CODE_HTTP_422 = 422  # 参数校验失败（FastAPI RequestValidationError，原生 {"detail": ...} 格式）
CODE_SERVER_ERROR = 500  # 未捕获异常（全局 Exception handler）
