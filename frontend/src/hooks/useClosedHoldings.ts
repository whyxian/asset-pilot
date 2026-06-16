import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteClosedHolding, fetchClosedHolding, fetchClosedHoldings, fetchClosedTransactions } from '@/api/endpoints'

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

/** 获取全部归档交易（统一历史交易查询） */
export function useClosedTransactions() {
  return useQuery({
    queryKey: ['closed-transactions'],
    queryFn: () => fetchClosedTransactions(),
  })
}

/** 删除归档持仓 */
export function useDeleteClosedHolding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteClosedHolding(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['closed-holdings'] })
      qc.invalidateQueries({ queryKey: ['closed-transactions'] })
    },
  })
}
