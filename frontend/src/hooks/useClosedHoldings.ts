import { useQuery } from '@tanstack/react-query'
import { fetchClosedHolding, fetchClosedHoldings } from '@/api/endpoints'

/** 获取全部归档持仓 */
export function useClosedHoldings() {
  return useQuery({
    queryKey: ['closed-holdings'],
    queryFn: fetchClosedHoldings,
  })
}

/** 获取单条归档持仓详情 */
export function useClosedHolding(id: number | null) {
  return useQuery({
    queryKey: ['closed-holdings', id],
    queryFn: () => fetchClosedHolding(id!),
    enabled: id !== null,
  })
}
