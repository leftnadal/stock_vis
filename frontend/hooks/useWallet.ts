// 지갑(보유·현금) TanStack Query 훅 (Slice 20b)
// mutation onSuccess = invalidateQueries (하우스 관례, 낙관적 갱신 미채택)
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { walletService } from '@/services/walletService'
import type { CashBalance, HoldingCreateInput, HoldingUpdateInput } from '@/types/wallet'

export const walletKeys = {
  all: ['wallet'] as const,
  holdings: () => [...walletKeys.all, 'holdings'] as const,
  cash: () => [...walletKeys.all, 'cash'] as const,
}

export function useHoldings() {
  return useQuery({
    queryKey: walletKeys.holdings(),
    queryFn: walletService.listHoldings,
  })
}

export function useCash() {
  return useQuery({
    queryKey: walletKeys.cash(),
    queryFn: walletService.listCash,
  })
}

export function useCreateHolding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: HoldingCreateInput) => walletService.createHolding(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: walletKeys.holdings() }),
  })
}

export function useUpdateHolding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: HoldingUpdateInput }) =>
      walletService.updateHolding(id, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: walletKeys.holdings() }),
  })
}

export function useDeleteHolding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => walletService.deleteHolding(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: walletKeys.holdings() }),
  })
}

export function useUpsertCash() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: CashBalance) => walletService.upsertCash(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: walletKeys.cash() }),
  })
}

export function useDeleteCash() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (currency: string) => walletService.deleteCash(currency),
    onSuccess: () => qc.invalidateQueries({ queryKey: walletKeys.cash() }),
  })
}
