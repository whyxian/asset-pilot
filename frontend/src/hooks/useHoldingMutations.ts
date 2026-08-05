import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { createHolding, updateHolding, deleteHolding } from '@/api/endpoints'
import { ApiError } from '@/api/types'
import type { HoldingCreate, HoldingUpdate, HoldingWithQuote } from '@/types'

/**
 * 持仓变更后需要联动失效的缓存：持仓 + 概览（依赖持仓）+ 交易（建仓/勘误自动生成）+ 现金（建仓/勘误联动流水）
 *
 * 返回 Promise 等待 refetch 完成 — onSuccess 返回 Promise 时
 * React Query 会让 isPending 一直保持到 Promise resolve，
 * 这样调用方只观察 isPending 就能在"提交完成 + 数据回来"之后才关闭对话框，
 * 避免出现"按钮已松开 / 对话框已关 / 表格还没更新"的 UX 间隙。
 */
function invalidateHoldingRelated(qc: QueryClient): Promise<void> {
  return Promise.all([
    qc.invalidateQueries({ queryKey: ['holdings'] }),
    qc.invalidateQueries({ queryKey: ['overview'] }),
    // 建仓/勘误自动生成的交易，让交易页也能立即看到
    qc.invalidateQueries({ queryKey: ['transactions'] }),
    // 建仓/勘误自动联动的现金流水（deposit+buy / buy / sell），让现金页也能立即看到
    qc.invalidateQueries({ queryKey: ['cash-balances'] }),
    qc.invalidateQueries({ queryKey: ['cash-flows'] }),
  ]).then(() => undefined)
}

/** 新增持仓 — 成功后等持仓列表 + 概览 refetch 完成 */
export function useCreateHolding() {
  const qc = useQueryClient()
  return useMutation<HoldingWithQuote, ApiError, HoldingCreate>({
    mutationFn: createHolding,
    onSuccess: async () => {
      await invalidateHoldingRelated(qc)
      toast.success('持仓已新增')
    },
    onError: (e) => toast.error('新增失败', { description: e.message }),
  })
}

/** 更新持仓 — 成功后等持仓列表 + 概览 refetch 完成 */
export function useUpdateHolding() {
  const qc = useQueryClient()
  return useMutation<
    HoldingWithQuote,
    ApiError,
    { ticker: string; asset_class: string; market: string; data: HoldingUpdate }
  >({
    mutationFn: ({ ticker, asset_class, market, data }) =>
      updateHolding(ticker, asset_class, market, data),
    onSuccess: async () => {
      await invalidateHoldingRelated(qc)
      toast.success('持仓已更新')
    },
    onError: (e) => toast.error('更新失败', { description: e.message }),
  })
}

/** 删除持仓 — 级联删除该品种的全部交易；等持仓/概览/交易 refetch 完成 */
export function useDeleteHolding() {
  const qc = useQueryClient()
  return useMutation<
    void,
    ApiError,
    { ticker: string; asset_class: string; market: string }
  >({
    mutationFn: ({ ticker, asset_class, market }) =>
      deleteHolding(ticker, asset_class, market),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['holdings'] }),
        qc.invalidateQueries({ queryKey: ['overview'] }),
        qc.invalidateQueries({ queryKey: ['transactions'] }),
        qc.invalidateQueries({ queryKey: ['closed-holdings'] }),
        qc.invalidateQueries({ queryKey: ['closed-transactions'] }),
        // 级联删除交易同时删除关联流水，现金余额变化
        qc.invalidateQueries({ queryKey: ['cash-balances'] }),
        qc.invalidateQueries({ queryKey: ['cash-flows'] }),
      ])
      toast.success('持仓已删除')
    },
    onError: (e) => toast.error('删除失败', { description: e.message }),
  })
}
