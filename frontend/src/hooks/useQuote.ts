import { useMutation } from '@tanstack/react-query'
import { fetchStockQuotes, fetchCryptoQuotes, fetchFundQuotes } from '@/api/endpoints'
import { ApiError } from '@/api/types'
import type { AssetQuote } from '@/types'

interface QuoteSearchParams {
  market: 'CN' | 'US' | 'CRYPTO'
  codes: string[]
  assetClass: 'STOCK' | 'FUND' | 'CRYPTO'
}

/** 行情查询 — 用户主动触发，根据市场+品种路由到对应 API */
export function useQuoteSearch() {
  return useMutation<AssetQuote[], ApiError, QuoteSearchParams>({
    mutationFn: async ({ market, codes, assetClass }) => {
      if (assetClass === 'STOCK') {
        return fetchStockQuotes(market as 'CN' | 'US', codes)
      }
      if (assetClass === 'CRYPTO') {
        return fetchCryptoQuotes(codes)
      }
      // FUND — CN 和 US 都走基金接口
      return fetchFundQuotes(market as 'CN' | 'US', codes)
    },
  })
}
