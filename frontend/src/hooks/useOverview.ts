import { useQuery } from '@tanstack/react-query'
import { fetchOverview } from '@/api/endpoints'

/** 获取概览统计 */
export function useOverview() {
  return useQuery({
    queryKey: ['overview'],
    queryFn: fetchOverview,
    staleTime: 60_000, // 1 分钟
  })
}
