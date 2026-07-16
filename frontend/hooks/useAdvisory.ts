// Advisory(권유) 읽기 화면 TanStack Query 훅 (Slice 20a)
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { advisoryService } from '@/services/advisoryService'

export const advisoryKeys = {
  all: ['advisory'] as const,
  latest: () => [...advisoryKeys.all, 'latest'] as const,
  summary: () => [...advisoryKeys.all, 'summary'] as const,
  knobs: () => [...advisoryKeys.all, 'knobs'] as const,
}

export function useLatestAdvisory() {
  return useQuery({
    queryKey: advisoryKeys.latest(),
    queryFn: advisoryService.getLatest,
  })
}

export function useAdvisorySummary() {
  return useQuery({
    queryKey: advisoryKeys.summary(),
    queryFn: advisoryService.getSummary,
  })
}

export function useAdvisoryKnobs() {
  return useQuery({
    queryKey: advisoryKeys.knobs(),
    queryFn: advisoryService.getKnobs,
  })
}

// [지금 진단] — 수동 진단 실행. 성공 시 latest·summary 재검증(knobs는 실행으로 안 변함).
export function useRunAdvisory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: advisoryService.run,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: advisoryKeys.latest() })
      qc.invalidateQueries({ queryKey: advisoryKeys.summary() })
    },
  })
}
