import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { createSnapshot, fetchAssetSnapshots, fetchSnapshots } from '@/api/endpoints'
import { STALE_TIME } from '@/lib/config'

/** 获取组合级快照列表（折线图数据源） */
export function useSnapshots(currency: string = 'CNY', limit: number = 365) {
  return useQuery({
    queryKey: ['snapshots', currency, limit],
    queryFn: () => fetchSnapshots(currency, limit),
    staleTime: STALE_TIME,
  })
}

/** 获取品种级快照 */
export function useAssetSnapshots(
  currency: string = 'CNY',
  ticker?: string,
  asset_class?: string,
  market?: string,
  limit: number = 365,
) {
  return useQuery({
    queryKey: ['asset-snapshots', currency, ticker || 'all', asset_class || 'all', market || 'all', limit],
    queryFn: () => fetchAssetSnapshots(currency, ticker, asset_class, market, limit),
    staleTime: STALE_TIME,
  })
}

/** 记录新快照（手动触发） */
export function useCreateSnapshot() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => createSnapshot(),
    onSuccess: () => {
      // 失效快照相关缓存
      qc.invalidateQueries({ queryKey: ['snapshots'] })
      qc.invalidateQueries({ queryKey: ['asset-snapshots'] })
      toast.success('快照已记录')
    },
    onError: (e: unknown) => toast.error('快照失败', {
      description: e instanceof Error ? e.message : '未知错误',
    }),
  })
}
