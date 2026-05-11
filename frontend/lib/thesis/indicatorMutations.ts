import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { thesisApi } from './api'
import { QUERY_KEYS } from './queries'
import type { IndicatorCreatePayload } from './types'

export function useAddIndicator(thesisId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: IndicatorCreatePayload) =>
      thesisApi.addIndicator(thesisId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.indicators(thesisId) })
    },
    onError: () => {
      toast.error('지표 추가에 실패했어요')
    },
  })
}

export function useRemoveIndicator(thesisId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (indicatorId: string) =>
      thesisApi.removeIndicator(thesisId, indicatorId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.indicators(thesisId) })
    },
    onError: () => {
      toast.error('지표 삭제에 실패했어요')
    },
  })
}

export function useToggleIndicator(thesisId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ indicatorId, isActive }: { indicatorId: string; isActive: boolean }) =>
      thesisApi.toggleIndicator(thesisId, indicatorId, isActive),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.indicators(thesisId) })
    },
    onError: () => {
      toast.error('변경에 실패했어요')
    },
  })
}
