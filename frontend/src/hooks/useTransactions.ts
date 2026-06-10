import { useQuery } from '@tanstack/react-query'
import { fetchTransactions } from '@/api/endpoints'

/** 获取交易记录列表 */
export function useTransactions(ticker?: string) {
  return useQuery({
    queryKey: ['transactions', ticker || 'all'],
    queryFn: () => fetchTransactions(ticker),
  })
}
