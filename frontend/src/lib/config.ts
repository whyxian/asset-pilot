/** 前端运行时配置 — 轮询间隔、缓存策略统一管理 */

/** 页面自动轮询间隔（秒）— 与后端调度器 30s 同步，每次更新即时反映 */
export const POLL_INTERVAL = 30_000

/** 全局 staleTime（毫秒）— 30s 内视为新鲜，不重复请求 */
export const STALE_TIME = 30_000

/** 查询失败重试次数 */
export const RETRY_COUNT = 1

/** toast 默认显示时长（毫秒）— 可在设置页自定义 */
export const TOAST_DURATION = 3000
