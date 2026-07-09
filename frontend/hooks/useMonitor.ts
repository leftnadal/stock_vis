// Monitor 허브 TanStack Query 훅 (MON-P3)
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { monitorService } from '@/services/monitorService'
import type { MonitorInput } from '@/types/monitor'

export const monitorKeys = {
  all: ['monitor'] as const,
  lists: () => [...monitorKeys.all, 'list'] as const,
  detail: (id: string) => [...monitorKeys.all, 'detail', id] as const,
  claims: (id: string) => [...monitorKeys.all, 'claims', id] as const,
  indicators: (id: string) => [...monitorKeys.all, 'indicators', id] as const,
  alerts: () => [...monitorKeys.all, 'alerts'] as const,
  alertsList: (params?: { unread?: boolean; deterioration?: boolean }) =>
    [...monitorKeys.alerts(), 'list', params ?? {}] as const,
  alertSummary: () => [...monitorKeys.alerts(), 'summary'] as const,
  sparkline: (id: string, window: number) =>
    [...monitorKeys.all, 'sparkline', id, window] as const,
}

export function useMonitors() {
  return useQuery({
    queryKey: monitorKeys.lists(),
    queryFn: monitorService.list,
  })
}

export function useMonitor(id: string) {
  return useQuery({
    queryKey: monitorKeys.detail(id),
    queryFn: () => monitorService.get(id),
    enabled: !!id,
  })
}

export function useCreateMonitor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: MonitorInput) => monitorService.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: monitorKeys.lists() }),
  })
}

export function useDeleteMonitor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => monitorService.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: monitorKeys.lists() }),
  })
}

export function useEvaluateMonitor() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => monitorService.evaluate(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: monitorKeys.detail(id) })
      qc.invalidateQueries({ queryKey: monitorKeys.lists() })
    },
  })
}

export function useMonitorClaims(id: string) {
  return useQuery({
    queryKey: monitorKeys.claims(id),
    queryFn: () => monitorService.listClaims(id),
    enabled: !!id,
  })
}

export function useIndicatorCatalog(scope: string) {
  return useQuery({
    queryKey: [...monitorKeys.all, 'catalog', scope] as const,
    queryFn: () => monitorService.getCatalog(scope),
    staleTime: 1000 * 60 * 60, // 카탈로그는 상수 — 1시간 캐시
  })
}

// ── 전이 알림 (MON-P3-ALERT) ──

export function useAlerts(params?: { unread?: boolean; deterioration?: boolean }) {
  return useQuery({
    queryKey: monitorKeys.alertsList(params),
    queryFn: () => monitorService.listAlerts(params),
  })
}

// 헤더 벨 배지 — 미인증 상태에선 enabled=false로 호출 자체를 막는다(호출 측 책임).
export function useAlertSummary(enabled = true) {
  return useQuery({
    queryKey: monitorKeys.alertSummary(),
    queryFn: () => monitorService.getAlertSummary(),
    enabled,
    staleTime: 1000 * 30,
    refetchInterval: 1000 * 60, // 1분 주기 갱신(다른 탭 읽음 처리 등 반영)
  })
}

export function useMarkAlertRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => monitorService.markAlertRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: monitorKeys.alerts() }),
  })
}

export function useMarkAllAlertsRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => monitorService.markAllAlertsRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: monitorKeys.alerts() }),
  })
}

// ── 상태밴드 스파크라인 (MON-P3-ALERT §6) ──

export function useSparkline(monitorId: string, window = 30, enabled = true) {
  return useQuery({
    queryKey: monitorKeys.sparkline(monitorId, window),
    queryFn: () => monitorService.getSparkline(monitorId, window),
    enabled: enabled && !!monitorId,
    staleTime: 1000 * 60 * 5,
  })
}
