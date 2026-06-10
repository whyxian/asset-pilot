import axios from 'axios'
import { ApiError } from './types'
import type { ApiResponse } from './types'

/** 统一 API 客户端
 *
 * - 开发时 Vite 代理把 /api 转发到 localhost:8000，baseURL 留空即可
 * - 生产环境可通过 VITE_API_BASE_URL 指定后端地址
 */
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 15000,
})

// 响应拦截器：自动解包 {code, message, data} → 返回 data；code≠0 时抛 ApiError
apiClient.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse<unknown>
    if (body.code === 0) {
      // 直接返回解包后的 data，调用方拿到的就是业务数据
      return body.data
    }
    throw new ApiError(body.code, body.message)
  },
  (error) => {
    if (error instanceof ApiError) throw error
    // 网络超时 / 连接失败 / 非 200 HTTP 状态
    const message = error.response?.data?.message || error.message || '网络请求失败'
    const code = error.response?.status || 0
    throw new ApiError(code, message)
  },
)

export default apiClient
