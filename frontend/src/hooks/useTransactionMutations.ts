import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { createTransaction, updateTransaction, deleteTransaction } from '@/api/endpoints'
import { ApiError } from '@/api/types'
import type { Transaction, TransactionCreate, TransactionUpdate } from '@/types'

/** 交易变更后需要联动失效的缓存：交易列表 + 持仓（重算了）+ 概览（依赖持仓）+ 历史持仓（可能触发归档） */
function invalidateTransactionRelated(qc: QueryClient) {
  qc.invalidateQueries({ queryKey: ['transactions'] })
  qc.invalidateQueries({ queryKey: ['holdings'] })
  qc.invalidateQueries({ queryKey: ['overview'] })
  qc.invalidateQueries({ queryKey: ['closed-holdings'] })
}

/** 新增交易记录 — 成功后失效交易/持仓/概览缓存 */
export function useCreateTransaction() {
  const qc = useQueryClient()
  return useMutation<Transaction, ApiError, TransactionCreate>({
    mutationFn: createTransaction,
    onSuccess: () => invalidateTransactionRelated(qc),
  })
}

/** 更新交易记录 — 成功后失效交易/持仓/概览缓存 */
export function useUpdateTransaction() {
  const qc = useQueryClient()
  return useMutation<Transaction, ApiError, { id: number; data: TransactionUpdate }>({
    mutationFn: ({ id, data }) => updateTransaction(id, data),
    onSuccess: () => invalidateTransactionRelated(qc),
  })
}

/** 删除交易记录 — 成功后失效交易/持仓/概览缓存 */
export function useDeleteTransaction() {
  const qc = useQueryClient()
  return useMutation<void, ApiError, number>({
    mutationFn: deleteTransaction,
    onSuccess: () => invalidateTransactionRelated(qc),
  })
}
