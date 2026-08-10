import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { createVariety, createWatchlist, deleteWatchlist, fetchWatchlistWithQuotes } from '@/api/endpoints'
import { POLL_INTERVAL } from '@/lib/config'
import type { AssetQuote, WatchlistItem, WatchlistWithQuote } from '@/types'

const KEY = ['watchlist', 'with-quotes'] as const

/** 自选 + 行情 — 30s 轮询（读后端缓存，与持仓页同模式） */
export function useWatchlistQuotes() {
  return useQuery<WatchlistWithQuote[]>({
    queryKey: KEY,
    queryFn: fetchWatchlistWithQuotes,
    refetchInterval: POLL_INTERVAL,
    refetchIntervalInBackground: false,
  })
}

/**
 * 收藏 — 乐观更新：点击立即出现，失败回滚。
 * 乐观条目带前端已拿到的 quote（REALTIME），避免出现闪 UNAVAILABLE 的空位。
 */
interface AddWatchlistVars {
  ticker: string
  asset_class: string
  market: string
  name: string
  quote?: AssetQuote
}

export function useAddWatchlist() {
  const qc = useQueryClient()
  return useMutation<WatchlistItem, Error, AddWatchlistVars, { prev?: WatchlistWithQuote[] }>({
    mutationFn: ({ ticker, asset_class, market, name }) =>
      createWatchlist({ ticker, asset_class, market, name }),
    onMutate: async (vars) => {
      await qc.cancelQueries({ queryKey: KEY })
      const prev = qc.getQueryData<WatchlistWithQuote[]>(KEY)
      const optimistic: WatchlistWithQuote = {
        id: -Date.now(), // 临时 id，成功后 invalidate 拉真实数据
        ticker: vars.ticker,
        asset_class: vars.asset_class,
        market: vars.market,
        name: vars.name,
        quote: vars.quote ?? null,
        status: vars.quote ? 'REALTIME' : 'UNAVAILABLE',
      }
      qc.setQueryData(KEY, [optimistic, ...(prev ?? [])])
      return { prev }
    },
    onError: (e, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(KEY, ctx.prev)
      toast.error('收藏失败', { description: e.message })
    },
    // mutationFn 返回 WatchlistItem，乐观缓存里是 WatchlistWithQuote；
    // 成功后 invalidate 拉真实数据对齐
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: KEY })
      toast.success('已加入自选')
    },
  })
}

/**
 * 取消收藏 — 乐观更新：点击立即消失，失败回滚。
 */
export function useRemoveWatchlist() {
  const qc = useQueryClient()
  return useMutation<void, Error, number, { prev?: WatchlistWithQuote[] }>({
    mutationFn: (id) => deleteWatchlist(id),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: KEY })
      const prev = qc.getQueryData<WatchlistWithQuote[]>(KEY)
      qc.setQueryData(KEY, (old: WatchlistWithQuote[] | undefined) =>
        (old ?? []).filter((w) => w.id !== id),
      )
      return { prev }
    },
    onError: (e, _id, ctx) => {
      if (ctx?.prev) qc.setQueryData(KEY, ctx.prev)
      toast.error('取消收藏失败', { description: e.message })
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: KEY })
      toast.success('已取消收藏')
    },
  })
}

/**
 * 显式添加到品种库（仅注册，不收藏）— 按钮状态由调用方本地管理。
 */
export function useAddVariety() {
  return useMutation({
    mutationFn: (data: { ticker: string; name: string; market: string; asset_class: string }) =>
      createVariety(data),
    onError: (e: unknown) => toast.error('添加失败', {
      description: e instanceof Error ? e.message : '未知错误',
    }),
  })
}
