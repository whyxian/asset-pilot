# API 约定（AssetPilot 后端）

> 从现有 API 层实际惯例提取（2026-09-03 生成，harness 自动维护）。
> 自定义内容请放在 `<!-- user:start -->` / `<!-- user:end -->` 之间，更新时原样保留。

<!-- user:start -->
<!-- 用户自定义区 -->
<!-- user:end -->

## 核心要点

- 统一返回格式 `{code, message, data}`，HTTP 状态恒为 200（错误码在 body）
- 错误码集中在 `backend/app/core/error_codes.py`，**禁止散落硬编码**
- 列表接口统一分页（`PaginatedResponse{data, total, page, page_size}`）
- 写操作尽量幂等（重复调用返回已有记录，不产生重复数据）

## 详细约定

### 1. 统一返回格式

成功：`{code: 0, message: "ok", data: ...}`；业务错误：`{code: 4xxxx, message, data: null}`。
API 层用 `success(data)` 包裹返回，不写 try/except；错误由 service 抛 `BusinessError`，全局异常处理器统一捕获。

### 2. 错误码

| code | 含义 | 场景 |
|------|------|------|
| 0 | 成功 | 全部正常响应 |
| 40001 | 业务校验失败 | 未识别品种/余额不足/费率超范围/归档前提不满足 |
| 40002 | 行情不可用 | 建仓/查询时数据源查无此代码 |
| 40401 | 资源不存在 | 持仓/交易/品种/归档/流水/自选不存在 |
| 404 / 422 / 500 | 框架错误 | 路由不存在 / 参数校验（原生 detail 格式）/ 未捕获异常 |

> 新增错误场景先到 `error_codes.py` 确认/新增码值，引用常量而非数字。

### 3. 路由与文件命名

- 文件 `asset_xxx_api.py`（或领域名如 `watchlist_api.py`），类与方法与文件对齐
- 前缀 `/api/v1`，tags 与领域一致（如 `tags=["watchlist"]`）
- 单条资源用路径参数（`/api/v1/watchlist/{id}`）；筛选用 query 参数

### 4. 分页

列表接口统一 `page`（≥1）+ `page_size`（默认 20，1-100），响应包 `PaginatedResponse[T]`（models/common.py）。已接入：交易/归档持仓/归档交易/现金流水。

### 5. 行情相关约定

- 用户请求只读缓存（QuoteCache）；`force_refresh=true` 显式绕过缓存拉最新（基金 15min 缓存）
- 行情状态三态 `QuoteStatus`：REALTIME / HISTORICAL（DB 兜底）/ UNAVAILABLE，前端按状态标记
- 查询查无结果抛 40002（不静默返回空数组）

### 6. 幂等与联动惯例

- 重复收藏自选 / 重复添加品种：幂等返回已有记录（不 500）
- 收藏自动注册品种；US/CRYPTO 按 ticker 对齐库里分类，CN 按三元组精确
- 外部请求超时 ≤ 前端 axios 15s 铁律（见根 CLAUDE.md「外部请求超时规范」）
