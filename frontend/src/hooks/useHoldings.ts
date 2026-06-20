import { useQuery } from '@tanstack/react-query'
import { fetchHoldingsWithQuotes } from '@/api/endpoints'
import type { HoldingsWithQuotesResponse } from '@/types'
import { POLL_INTERVAL } from '@/lib/config'

/** 获取持仓 + 实时行情 — 概览页和持仓页共享同一个 query key */
export function useHoldings() {
  return useQuery<HoldingsWithQuotesResponse>({
    queryKey: ['holdings', 'with-quotes'],
    queryFn: fetchHoldingsWithQuotes,
    refetchInterval: POLL_INTERVAL,
    refetchIntervalInBackground: false,
  })
}
