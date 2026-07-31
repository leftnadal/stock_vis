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

// 목표 생성(SLICE20BF2, POST). 목표는 knobs·summary(갭·모드)·latest(권유 가능성) 전부에
// 영향 → 3키 모두 재검증(부재 화면 → 권유 화면 전환). updateKnobs(knobs만)와 다름.
export function useCreateGoal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: advisoryService.createGoal,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: advisoryKeys.knobs() })
      qc.invalidateQueries({ queryKey: advisoryKeys.latest() })
      qc.invalidateQueries({ queryKey: advisoryKeys.summary() })
    },
  })
}

// 손잡이/목표 저장(SLICE20B). **저장 ≠ 진단 실행(D2)** — knobs만 재검증하고
// latest/summary는 건드리지 않는다(진단은 [지금 진단] 수동 경유).
export function useUpdateKnobs() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: advisoryService.updateKnobs,
    onSuccess: () => qc.invalidateQueries({ queryKey: advisoryKeys.knobs() }),
  })
}
