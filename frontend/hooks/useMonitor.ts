// Monitor 허브 TanStack Query 훅 (MON-P3)
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { monitorService } from '@/services/monitorService'
import type { CloseClaimInput, MonitorInput } from '@/types/monitor'

export const monitorKeys = {
  all: ['monitor'] as const,
  lists: () => [...monitorKeys.all, 'list'] as const,
  detail: (id: string) => [...monitorKeys.all, 'detail', id] as const,
  // Claim은 사용자 전체 단일 목록(BE가 monitor로 필터하지 않음 — 모니터별 필터는
  // 클라이언트단). list/detail 페이지가 같은 키를 공유해 요청을 dedupe한다.
  claims: () => [...monitorKeys.all, 'claims'] as const,
  indicators: (id: string) => [...monitorKeys.all, 'indicators', id] as const,
  closePreview: (claimId: string) => [...monitorKeys.all, 'closePreview', claimId] as const,
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

// 사용자 전체 Claim (모니터 무관) — 리스트 페이지의 상태 세그먼트·"n중 m 마감" 파생용.
export function useClaims() {
  return useQuery({
    queryKey: monitorKeys.claims(),
    queryFn: () => monitorService.listClaims(),
  })
}

// 특정 모니터의 Claim만 — BE가 monitor로 필터하지 않으므로 전체 목록을 클라단에서 거른다
// (useClaims와 동일 쿼리키를 공유해 상세·리스트 페이지 간 요청을 dedupe).
export function useMonitorClaims(id: string) {
  const query = useQuery({
    queryKey: monitorKeys.claims(),
    queryFn: () => monitorService.listClaims(),
    enabled: !!id,
  })
  return { ...query, data: query.data?.filter((c) => c.monitor === id) }
}

export function useIndicators(monitorId: string) {
  return useQuery({
    queryKey: monitorKeys.indicators(monitorId),
    queryFn: () => monitorService.listIndicators(monitorId),
    enabled: !!monitorId,
  })
}

export function useIndicatorCatalog(scope: string) {
  return useQuery({
    queryKey: [...monitorKeys.all, 'catalog', scope] as const,
    queryFn: () => monitorService.getCatalog(scope),
    staleTime: 1000 * 60 * 60, // 카탈로그는 상수 — 1시간 캐시
  })
}

// L계열 가격 제안 (TIMING-P2 §3) — 심볼 확정 + enabled일 때만 조회(빌더 4단계).
export function useScenarioSuggest(symbol: string, enabled: boolean) {
  return useQuery({
    queryKey: [...monitorKeys.all, 'scenarioSuggest', symbol] as const,
    queryFn: () => monitorService.scenarioSuggest(symbol),
    enabled: enabled && symbol.trim() !== '',
    staleTime: 1000 * 60 * 5,
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

// ── 가설 마감 (MON-CLOSE-UI Phase 2) ──

// 마감 모달 프리필 — 무상태(claim 상태와 무관하게 항상 monitor의 현재 값을 반환).
export function useClosePreview(claimId: string, enabled = true) {
  return useQuery({
    queryKey: monitorKeys.closePreview(claimId),
    queryFn: () => monitorService.closePreview(claimId),
    enabled: enabled && !!claimId,
  })
}

export function useCloseClaim() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      claimId,
      payload,
    }: {
      claimId: string
      monitorId: string
      payload: CloseClaimInput
    }) => monitorService.closeClaim(claimId, payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: monitorKeys.claims() })
      qc.invalidateQueries({ queryKey: monitorKeys.detail(vars.monitorId) })
      qc.invalidateQueries({ queryKey: monitorKeys.lists() })
    },
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
