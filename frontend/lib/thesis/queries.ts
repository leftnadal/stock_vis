import { useQuery } from '@tanstack/react-query'
import { thesisApi } from './api'
import { USE_MOCK } from './mock'

export const QUERY_KEYS = {
  list:        ['thesis', 'list'] as const,
  detail:      (id: string) => ['thesis', id] as const,
  dashboard:   (id: string) => ['thesis', id, 'dashboard'] as const,
  indicators:  (id: string) => ['thesis', id, 'indicators'] as const,
  alerts:      ['thesis', 'alerts'] as const,
  alertsCount: ['thesis', 'alerts-count'] as const,
} as const

// 전역 QueryProvider: staleTime=5min, retry=2, refetchOnWindowFocus=false
// thesis 전용 차이점만 override
const THESIS_DEFAULTS = {
  refetchOnWindowFocus: true as const,
  retry: 1,
}

export function useThesisList(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: QUERY_KEYS.list,
    queryFn: () => thesisApi.list(),
    ...THESIS_DEFAULTS,
    ...options,
  })
}

export function useThesis(thesisId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.detail(thesisId),
    queryFn: () => thesisApi.get(thesisId),
    enabled: !USE_MOCK && !!thesisId,
    ...THESIS_DEFAULTS,
  })
}

export function useDashboard(thesisId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.dashboard(thesisId),
    queryFn: () => thesisApi.dashboard(thesisId),
    enabled: !USE_MOCK && !!thesisId,
    ...THESIS_DEFAULTS,
  })
}

export function useIndicators(thesisId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.indicators(thesisId),
    queryFn: () => thesisApi.listIndicators(thesisId),
    enabled: !USE_MOCK && !!thesisId,
    ...THESIS_DEFAULTS,
  })
}

export function useAlerts(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: QUERY_KEYS.alerts,
    queryFn: async () => {
      const response = await thesisApi.listAlerts()
      return response.alerts
    },
    ...THESIS_DEFAULTS,
    ...options,
  })
}

// 벨 아이콘 전용 — 백엔드 unread_count 직접 사용
export function useUnreadAlertCount() {
  const { data } = useQuery({
    queryKey: QUERY_KEYS.alertsCount,
    queryFn: () => thesisApi.listAlerts(),
    enabled: !USE_MOCK,
    staleTime: 1000 * 60 * 10,
    refetchOnWindowFocus: true,
    retry: 1,
  })
  return data?.unread_count ?? 0
}
