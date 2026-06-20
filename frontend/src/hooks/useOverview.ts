import { useQuery } from '@tanstack/react-query'
import { fetchOverview } from '@/api/endpoints'
import { POLL_INTERVAL } from '@/lib/config'

/** 获取概览统计 */
export function useOverview(currency: string = 'CNY') {
  return useQuery({
    queryKey: ['overview', currency],
    queryFn: () => fetchOverview(currency),
    refetchInterval: POLL_INTERVAL,
    refetchIntervalInBackground: false,
  })
}
