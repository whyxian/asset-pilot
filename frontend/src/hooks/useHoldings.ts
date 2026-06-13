import { useQuery } from '@tanstack/react-query'
import { fetchHoldingsWithQuotes } from '@/api/endpoints'

/** 获取持仓 + 实时行情 — 概览页和持仓页共享同一个 query key */
export function useHoldings() {
  return useQuery({
    queryKey: ['holdings', 'with-quotes'],
    queryFn: fetchHoldingsWithQuotes,
    refetchInterval: 60_000, // 每 60 秒自动轮询行情
    refetchIntervalInBackground: false, // 标签页隐藏时暂停轮询
  })
}
