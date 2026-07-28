import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { deleteClosedHolding, fetchClosedHolding, fetchClosedHoldings, fetchClosedTransactions } from '@/api/endpoints'

/** 获取全部归档持仓（分页） */
export function useClosedHoldings(page: number, pageSize: number) {
  return useQuery({
    queryKey: ['closed-holdings', page, pageSize],
    queryFn: () => fetchClosedHoldings(page, pageSize),
    placeholderData: (prev) => prev,
  })
}

/** 获取单条归档持仓详情 */
export function useClosedHolding(id: number | null) {
  return useQuery({
    queryKey: ['closed-holdings', 'detail', id],
    queryFn: () => fetchClosedHolding(id!),
    enabled: id !== null,
  })
}

/** 获取全部归档交易（分页） */
export function useClosedTransactions(page: number, pageSize: number) {
  return useQuery({
    queryKey: ['closed-transactions', page, pageSize],
    queryFn: () => fetchClosedTransactions(page, pageSize),
    placeholderData: (prev) => prev,
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
      toast.success('历史持仓已删除')
    },
    onError: (e: unknown) => toast.error('删除失败', {
      description: e instanceof Error ? e.message : '未知错误',
    }),
  })
}
