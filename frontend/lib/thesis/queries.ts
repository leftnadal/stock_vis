import { useQuery } from '@tanstack/react-query'
import { thesisApi } from './api'

const QUERY_KEYS = {
  list:        ['thesis', 'list'] as const,
  detail:      (id: string) => ['thesis', id] as const,
  dashboard:   (id: string) => ['thesis', id, 'dashboard'] as const,
  indicators:  (id: string) => ['thesis', id, 'indicators'] as const,
  alerts:      (id?: string) => ['thesis', 'alerts', id ?? 'all'] as const,
  alertsCount: ['thesis', 'alerts-count'] as const,
} as const

// 전역 QueryProvider: staleTime=5min, retry=2, refetchOnWindowFocus=false
// thesis 전용 차이점만 override
const THESIS_DEFAULTS = {
  refetchOnWindowFocus: true as const,
  retry: 1,
}

export function useThesisList() {
  return useQuery({
    queryKey: QUERY_KEYS.list,
    queryFn: () => thesisApi.list(),
    ...THESIS_DEFAULTS,
  })
}

export function useThesis(thesisId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.detail(thesisId),
    queryFn: () => thesisApi.get(thesisId),
    enabled: !!thesisId,
    ...THESIS_DEFAULTS,
  })
}

export function useDashboard(thesisId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.dashboard(thesisId),
    queryFn: () => thesisApi.dashboard(thesisId),
    enabled: !!thesisId,
    ...THESIS_DEFAULTS,
  })
}

export function useIndicators(thesisId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.indicators(thesisId),
    queryFn: () => thesisApi.listIndicators(thesisId),
    enabled: !!thesisId,
    ...THESIS_DEFAULTS,
  })
}

export function useAlerts(thesisId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.alerts(thesisId),
    queryFn: () => thesisApi.listAlerts(thesisId),
    ...THESIS_DEFAULTS,
  })
}

// 벨 아이콘 전용 — 기존 alerts 목록 API로 프론트 filter
// alertsCount와 alerts는 다른 queryKey이므로 staleTime 충돌 없음
export function useUnreadAlertCount() {
  const { data } = useQuery({
    queryKey: QUERY_KEYS.alertsCount,
    queryFn: () => thesisApi.listAlerts(),
    staleTime: 1000 * 60 * 10,
    refetchOnWindowFocus: true,
    retry: 1,
  })
  return data?.filter(a => !a.is_read).length ?? 0
}
