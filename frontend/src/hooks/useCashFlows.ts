import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cashDeposit, cashWithdraw, fetchCashBalances, fetchCashFlows } from '@/api/endpoints'
import type { CashDepositData, CashWithdrawData } from '@/api/endpoints'

export function useCashBalances() {
  return useQuery({
    queryKey: ['cash-balances'],
    queryFn: fetchCashBalances,
    refetchInterval: 60_000,
  })
}

export function useCashFlows(limit = 100) {
  return useQuery({
    queryKey: ['cash-flows', limit],
    queryFn: () => fetchCashFlows(limit),
    refetchInterval: 60_000,
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
