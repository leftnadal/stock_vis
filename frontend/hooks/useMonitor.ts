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
