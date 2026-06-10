/** API 响应统一包装格式 */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

/** API 业务异常 */
export class ApiError extends Error {
  constructor(
    public code: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}
