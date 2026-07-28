import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cashDeposit, cashWithdraw, fetchCashBalances, fetchCashFlows } from '@/api/endpoints'
import type { CashDepositData, CashWithdrawData } from '@/api/endpoints'

export function useCashBalances(currency: string = 'CNY') {
  return useQuery({
    queryKey: ['cash-balances', currency],
    queryFn: () => fetchCashBalances(currency),
    refetchInterval: 60_000,
  })
}

export function useCashFlows(page: number = 1, pageSize: number = 20) {
  return useQuery({
    queryKey: ['cash-flows', page, pageSize],
    queryFn: () => fetchCashFlows(page, pageSize),
    refetchInterval: 60_000,
    placeholderData: (prev) => prev,
  })
}

export function useCashDeposit() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CashDepositData) => cashDeposit(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cash-balances'] })
      qc.invalidateQueries({ queryKey: ['cash-flows'] })
    },
  })
}

export function useCashWithdraw() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CashWithdrawData) => cashWithdraw(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cash-balances'] })
      qc.invalidateQueries({ queryKey: ['cash-flows'] })
    },
  })
}
