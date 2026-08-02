import { useEffect, useState } from 'react'

/**
 * 当前时间戳 hook — 每隔 intervalMs 自动刷新一次
 *
 * 用于渲染时需要"现在"的场景（如持仓天数），避免直接在渲染期调用 Date.now()
 * （react-hooks/purity 规则禁止在渲染期调用不纯函数）
 */
export function useNow(intervalMs = 60_000): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(t)
  }, [intervalMs])

  return now
}
