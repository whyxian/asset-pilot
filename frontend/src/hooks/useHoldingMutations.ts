import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { createHolding, updateHolding, deleteHolding } from '@/api/endpoints'
import { ApiError } from '@/api/types'
import type { HoldingCreate, HoldingUpdate, HoldingWithQuote } from '@/types'

/**
 * 持仓变更后需要联动失效的缓存：持仓 + 概览（依赖持仓）
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
  ]).then(() => undefined)
}

/** 新增持仓 — 成功后等持仓列表 + 概览 refetch 完成 */
export function useCreateHolding() {
  const qc = useQueryClient()
  return useMutation<HoldingWithQuote, ApiError, HoldingCreate>({
    mutationFn: createHolding,
    onSuccess: () => invalidateHoldingRelated(qc),
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
    onSuccess: () => invalidateHoldingRelated(qc),
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
    onSuccess: () => Promise.all([
      qc.invalidateQueries({ queryKey: ['holdings'] }),
      qc.invalidateQueries({ queryKey: ['overview'] }),
      qc.invalidateQueries({ queryKey: ['transactions'] }),
      qc.invalidateQueries({ queryKey: ['closed-holdings'] }),
      qc.invalidateQueries({ queryKey: ['closed-transactions'] }),
    ]).then(() => undefined),
  })
}
