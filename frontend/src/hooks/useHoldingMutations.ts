import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createHolding, updateHolding, deleteHolding } from '@/api/endpoints'
import { ApiError } from '@/api/types'
import type { HoldingCreate, HoldingUpdate, HoldingWithQuote } from '@/types'

/** 新增持仓 — 成功后刷新持仓列表缓存 */
export function useCreateHolding() {
  const qc = useQueryClient()
  return useMutation<HoldingWithQuote, ApiError, HoldingCreate>({
    mutationFn: createHolding,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['holdings'] })
    },
  })
}

/** 更新持仓 — 成功后刷新持仓列表缓存 */
export function useUpdateHolding() {
  const qc = useQueryClient()
  return useMutation<HoldingWithQuote, ApiError, { ticker: string; data: HoldingUpdate }>({
    mutationFn: ({ ticker, data }) => updateHolding(ticker, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['holdings'] })
    },
  })
}

/** 删除持仓 — 成功后刷新持仓列表缓存 */
export function useDeleteHolding() {
  const qc = useQueryClient()
  return useMutation<void, ApiError, string>({
    mutationFn: deleteHolding,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['holdings'] })
    },
  })
}
