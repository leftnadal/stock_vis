// Monitor 허브 API 클라이언트 (MON-P3)
// authAxios baseURL에 이미 /api/v1 포함 → 경로에 중복 금지 (common-bug #19)
import { authAxios } from '@/lib/api/authAxios'
import type {
  AlertEvent,
  AlertSummary,
  CatalogEntry,
  Claim,
  EvaluateResult,
  Monitor,
  MonitorIndicator,
  MonitorInput,
  SparklineResponse,
} from '@/types/monitor'

// DRF 페이지네이션 대응: {results:[...]} 또는 배열 모두 수용
function unwrapList<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[]
  if (data && typeof data === 'object' && 'results' in data) {
    return (data as { results: T[] }).results
  }
  return []
}

export const monitorService = {
  list: async (): Promise<Monitor[]> => {
    const { data } = await authAxios.get('/monitor/monitors/')
    return unwrapList<Monitor>(data)
  },
  get: async (id: string): Promise<Monitor> => {
    const { data } = await authAxios.get(`/monitor/monitors/${id}/`)
    return data
  },
  create: async (payload: MonitorInput): Promise<Monitor> => {
    const { data } = await authAxios.post('/monitor/monitors/', payload)
    return data
  },
  update: async (id: string, payload: Partial<MonitorInput>): Promise<Monitor> => {
    const { data } = await authAxios.patch(`/monitor/monitors/${id}/`, payload)
    return data
  },
  remove: async (id: string): Promise<void> => {
    await authAxios.delete(`/monitor/monitors/${id}/`)
  },
  evaluate: async (id: string): Promise<EvaluateResult> => {
    const { data } = await authAxios.post(`/monitor/monitors/${id}/evaluate/`)
    return data
  },

  getCatalog: async (scope: string): Promise<CatalogEntry[]> => {
    const { data } = await authAxios.get('/monitor/catalog/', { params: { scope } })
    return data.indicators ?? []
  },

  listIndicators: async (monitorId?: string): Promise<MonitorIndicator[]> => {
    const { data } = await authAxios.get('/monitor/indicators/', {
      params: monitorId ? { monitor: monitorId } : undefined,
    })
    return unwrapList<MonitorIndicator>(data)
  },
  createIndicator: async (
    payload: Partial<MonitorIndicator> & { monitor: string; name: string; indicator_type: string }
  ): Promise<MonitorIndicator> => {
    const { data } = await authAxios.post('/monitor/indicators/', payload)
    return data
  },

  listClaims: async (monitorId?: string): Promise<Claim[]> => {
    const { data } = await authAxios.get('/monitor/claims/', {
      params: monitorId ? { monitor: monitorId } : undefined,
    })
    return unwrapList<Claim>(data)
  },
  createClaim: async (
    payload: { monitor: string; assertion: string; deadline?: string | null }
  ): Promise<Claim> => {
    const { data } = await authAxios.post('/monitor/claims/', payload)
    return data
  },

  // ── 전이 알림 (MON-P3-ALERT) ──
  listAlerts: async (params?: {
    unread?: boolean
    deterioration?: boolean
  }): Promise<AlertEvent[]> => {
    const query: Record<string, string> = {}
    if (params?.unread) query.unread = 'true'
    if (params?.deterioration) query.deterioration = 'true'
    const { data } = await authAxios.get('/monitor/alerts/', { params: query })
    return unwrapList<AlertEvent>(data)
  },
  getAlertSummary: async (): Promise<AlertSummary> => {
    const { data } = await authAxios.get('/monitor/alerts/summary/')
    return data
  },
  markAlertRead: async (id: string): Promise<AlertEvent> => {
    const { data } = await authAxios.post(`/monitor/alerts/${id}/read/`)
    return data
  },
  markAllAlertsRead: async (): Promise<{ marked_read: number }> => {
    const { data } = await authAxios.post('/monitor/alerts/read_all/')
    return data
  },

  // ── 상태밴드 스파크라인 (MON-P3-ALERT §6) ──
  getSparkline: async (monitorId: string, window = 30): Promise<SparklineResponse> => {
    const { data } = await authAxios.get(`/monitor/monitors/${monitorId}/sparkline/`, {
      params: { window },
    })
    return data
  },
}
