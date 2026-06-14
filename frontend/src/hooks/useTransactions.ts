import { useQuery } from '@tanstack/react-query'
import { fetchTransactions } from '@/api/endpoints'

/** 获取交易记录列表（三元组筛选都可选） */
export function useTransactions(ticker?: string, asset_class?: string, market?: string) {
  return useQuery({
    queryKey: ['transactions', ticker || 'all', asset_class || 'all', market || 'all'],
    queryFn: () => fetchTransactions(ticker, asset_class, market),
  })
}
