import { useQuery } from '@tanstack/react-query'
import { fetchStockQuotes, fetchCryptoQuotes, fetchFundQuotes } from '@/api/endpoints'
import type { AssetQuote } from '@/types'

export interface QuoteSearchParams {
  market: 'CN' | 'US' | 'CRYPTO'
  codes: string[]
  assetClass: 'STOCK' | 'FUND' | 'CRYPTO'
}

/**
 * 行情查询 — 弹窗打开时按 query 拉取
 *
 * 用 useQuery 而非 useMutation：查询是幂等的，useQuery 内置 dedupe（StrictMode
 * 双跑只发一次请求）+ 缓存（弹窗重开不重复请求，卸载后数据不丢）。
 * enabled 由弹窗 open 状态控制，打开才触发。
 */
export function useQuoteSearch(query: QuoteSearchParams | null | undefined, enabled: boolean) {
  return useQuery<AssetQuote[]>({
    queryKey: ['quote-search', query?.market ?? '', (query?.codes ?? []).join(','), query?.assetClass ?? ''],
    queryFn: async () => {
      if (!query) return []
      const { market, codes, assetClass } = query
      if (assetClass === 'STOCK') {
        return fetchStockQuotes(market as 'CN' | 'US', codes)
      }
      if (assetClass === 'CRYPTO') {
        return fetchCryptoQuotes(codes)
      }
      // FUND — CN 和 US 都走基金接口
      return fetchFundQuotes(market as 'CN' | 'US', codes)
    },
    enabled,
  })
}
