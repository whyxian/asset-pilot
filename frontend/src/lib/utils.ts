import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** 安全转数字：处理后端 Decimal 序列化为字符串的情况 */
export function toNum(v: number | string | null | undefined): number {
  if (v == null) return 0
  return typeof v === 'string' ? parseFloat(v) : v
}

/** 格式化价格/金额 — 不丢精度，不猜小数位
 *
 *  核心原则：后端传什么精度就显什么精度。
 *  - 字符串输入（后端 Decimal 序列化）：保留原有小数位数，仅去掉尾随零
 *  - 数字输入（前端计算值）：用最多 10 位有效数字格式化
 *  - 传 decimals 参数可强制固定小数位（用于概览总金额等）
 */
export function formatPrice(value: number | string | null | undefined, currency = '', decimals?: number): string {
  const prefix: Record<string, string> = { CNY: '¥', USD: '$' }
  const sym = prefix[currency] || ''

  if (value == null || value === '') return `${sym}N/A`

  // ── 字符串输入：来自后端 Decimal，保留其精度 ──
  if (typeof value === 'string') {
    const m = value.match(/^(-?\d+)(?:\.(\d+))?$/)
    if (!m) return `${sym}${value}` // fallback
    const intPart = m[1]
    const num = parseFloat(value)
    if (num === 0) return `${sym}0`
    // 指定 decimals 时按固定小数位截取
    if (decimals !== undefined) {
      return `${sym}${num.toFixed(decimals)}`
    }
    // 不指定 decimals：保留全部小数位，仅去掉尾随零
    let decPart = (m[2] ?? '').replace(/0+$/, '')
    if (!decPart) return `${sym}${intPart}`
    return `${sym}${intPart}.${decPart}`
  }

  // ── 数字输入：前端计算值（总市值等） ──
  if (value === 0) return `${sym}0`
  if (decimals !== undefined) return `${sym}${value.toFixed(decimals)}`
  return `${sym}${value.toLocaleString(undefined, {
    maximumSignificantDigits: 10,
    useGrouping: false,
  })}`
}

/** 格式化百分比（始终保留 2 位小数） */
export function formatPct(value: number | null | undefined, signed = true): string {
  if (value == null) return 'N/A'
  const sign = signed && value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}
