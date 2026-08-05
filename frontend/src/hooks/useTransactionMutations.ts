import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { createTransaction, updateTransaction, deleteTransaction } from '@/api/endpoints'
import { ApiError } from '@/api/types'
import type { Transaction, TransactionCreate, TransactionUpdate } from '@/types'

/**
 * 交易变更后需要联动失效的缓存：交易列表 + 持仓（重算了）+ 概览（依赖持仓）+ 归档表（可能触发归档）+ 现金（买卖自动联动流水）
 *
 * 返回 Promise 等待 refetch 完成 — onSuccess 返回 Promise 时
 * React Query 会让 isPending 一直保持到 Promise resolve，
 * 调用方只看 isPending 就能在数据真正回来之后才关闭对话框。
 */
function invalidateTransactionRelated(qc: QueryClient): Promise<void> {
  return Promise.all([
    qc.invalidateQueries({ queryKey: ['transactions'] }),
    qc.invalidateQueries({ queryKey: ['holdings'] }),
    qc.invalidateQueries({ queryKey: ['overview'] }),
    qc.invalidateQueries({ queryKey: ['closed-holdings'] }),
    qc.invalidateQueries({ queryKey: ['closed-transactions'] }),
    // 买卖交易自动联动的现金流水（buy 扣款 / sell 入账），让现金页也能立即看到
    qc.invalidateQueries({ queryKey: ['cash-balances'] }),
    qc.invalidateQueries({ queryKey: ['cash-flows'] }),
  ]).then(() => undefined)
}

/** 新增交易记录 — 成功后失效交易/持仓/概览缓存 */
export function useCreateTransaction() {
  const qc = useQueryClient()
  return useMutation<Transaction, ApiError, TransactionCreate>({
    mutationFn: createTransaction,
    onSuccess: async () => {
      await invalidateTransactionRelated(qc)
      toast.success('交易已记录')
    },
    onError: (e) => toast.error('记录失败', { description: e.message }),
  })
}

/** 更新交易记录 — 成功后失效交易/持仓/概览缓存 */
export function useUpdateTransaction() {
  const qc = useQueryClient()
  return useMutation<Transaction, ApiError, { id: number; data: TransactionUpdate }>({
    mutationFn: ({ id, data }) => updateTransaction(id, data),
    onSuccess: async () => {
      await invalidateTransactionRelated(qc)
      toast.success('交易已更新')
    },
    onError: (e) => toast.error('更新失败', { description: e.message }),
  })
}

/** 删除交易记录 — 成功后失效交易/持仓/概览缓存 */
export function useDeleteTransaction() {
  const qc = useQueryClient()
  return useMutation<void, ApiError, number>({
    mutationFn: deleteTransaction,
    onSuccess: async () => {
      await invalidateTransactionRelated(qc)
      toast.success('交易已删除')
    },
    onError: (e) => toast.error('删除失败', { description: e.message }),
  })
}
