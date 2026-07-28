import { useQuery } from '@tanstack/react-query'
import { fetchTransactions } from '@/api/endpoints'

/** 获取交易记录列表（三元组筛选都可选，分页） */
export function useTransactions(page: number, pageSize: number, ticker?: string, asset_class?: string, market?: string) {
  return useQuery({
    queryKey: ['transactions', page, pageSize, ticker || 'all', asset_class || 'all', market || 'all'],
    queryFn: () => fetchTransactions(page, pageSize, ticker, asset_class, market),
    placeholderData: (prev) => prev,
  })
}
