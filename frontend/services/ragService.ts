import axios from 'axios'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import type {
  Basket,
  BasketItem,
  Session,
  Message,
  SSEEvent,
} from '@/types/rag'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// API 인스턴스 생성
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - 토큰 추가
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor - 응답 데이터 추출 및 에러 처리
api.interceptors.response.use(
  (response) => {
    // Backend가 { success: true, data: ... } 형식으로 응답하는 경우 data 추출
    if (response.data && response.data.success === true && response.data.data !== undefined) {
      response.data = response.data.data
    }
    return response
  },
  (error) => {
    console.error('Response error:', error)

    if (!error.response) {
      console.error('Network error - no response')
      error.message = '서버와 연결할 수 없습니다.'
    } else {
      const { status, data } = error.response
      console.error(`Server error - status: ${status}`, data)

      if (status === 401) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      }
    }

    return Promise.reject(error)
  }
)

// Basket API
export const basketService = {
  async getList(): Promise<Basket[]> {
    const response = await api.get('/rag/baskets/')
    // Response interceptor already extracts data from wrapped response
    // Handle both array and paginated response
    const data = response.data
    return Array.isArray(data) ? data : (data.results ?? [])
  },

  async create(data: { name: string; description?: string }): Promise<Basket> {
    const response = await api.post('/rag/baskets/', data)
    return response.data
  },

  async getDetail(id: number): Promise<Basket> {
    const response = await api.get(`/rag/baskets/${id}/`)
    return response.data
  },

  async update(id: number, data: { name?: string; description?: string }): Promise<Basket> {
    const response = await api.patch(`/rag/baskets/${id}/`, data)
    return response.data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/rag/baskets/${id}/`)
  },

  async addItem(id: number, item: Omit<BasketItem, 'id' | 'added_at'>): Promise<BasketItem> {
    const response = await api.post(`/rag/baskets/${id}/add-item/`, item)
    return response.data
  },

  async removeItem(id: number, itemId: number): Promise<void> {
    await api.delete(`/rag/baskets/${id}/items/${itemId}/`)
  },

  async clear(id: number): Promise<void> {
    await api.delete(`/rag/baskets/${id}/clear/`)
  },

  async addStockData(
    id: number,
    symbol: string,
    dataTypes: string[]
  ): Promise<{
    message: string;
    items: BasketItem[];
    total_units_added: number;
    basket_current_units: number;
    basket_remaining_units: number;
  }> {
    const response = await api.post(`/rag/baskets/${id}/add-stock-data/`, {
      symbol,
      data_types: dataTypes,
    })
    return response.data
  },
}

// Session API
export const sessionService = {
  async getList(): Promise<Session[]> {
    const response = await api.get('/rag/sessions/')
    const data = response.data
    return Array.isArray(data) ? data : (data.results ?? [])
  },

  async create(data: { basket: number; title?: string }): Promise<Session> {
    // Backend serializer expects basket_id, not basket
    const response = await api.post('/rag/sessions/', {
      basket_id: data.basket,
      title: data.title,
    })
    return response.data
  },

  async getDetail(id: number): Promise<Session> {
    const response = await api.get(`/rag/sessions/${id}/`)
    return response.data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/rag/sessions/${id}/`)
  },

  async getMessages(id: number): Promise<Message[]> {
    const response = await api.get(`/rag/sessions/${id}/messages/`)
    const data = response.data
    return Array.isArray(data) ? data : (data.results ?? [])
  },
}

// Pipeline 버전 타입
export type PipelineVersion = 'lite' | 'v2' | 'final'

// SSE Streaming
export const streamAnalysis = async (
  sessionId: number,
  message: string,
  onEvent: (event: SSEEvent) => void,
  onError: (error: Error) => void,
  pipeline: PipelineVersion = 'final'  // 기본값: 최적화된 파이프라인
): Promise<void> => {
  const token = localStorage.getItem('access_token')

  class RetriableError extends Error {}
  class FatalError extends Error {}

  console.log('[SSE] Starting stream:', { sessionId, message, pipeline, token: token ? 'present' : 'missing' })

  await fetchEventSource(`${API_URL}/rag/sessions/${sessionId}/chat/stream/?pipeline=${pipeline}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
      'Authorization': token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify({ message }),

    async onopen(response) {
      console.log('[SSE] Connection opened:', { status: response.status, ok: response.ok })
      if (response.ok) {
        return // 연결 성공
      } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
        // 클라이언트 에러 (재시도 불가)
        throw new FatalError(`HTTP ${response.status}`)
      } else {
        // 서버 에러 또는 429 (재시도 가능)
        throw new RetriableError(`HTTP ${response.status}`)
      }
    },

    onmessage(event) {
      console.log('[SSE] Message received:', event.data?.substring(0, 100))
      try {
        const data: SSEEvent = JSON.parse(event.data)
        onEvent(data)
      } catch (err) {
        console.error('[SSE] Failed to parse event:', err)
      }
    },

    onerror(err) {
      console.error('[SSE] Error:', err)
      if (err instanceof FatalError) {
        throw err // 재시도 중단
      }
      // RetriableError는 자동으로 재시도됨
      onError(err as Error)
    },

    openWhenHidden: true, // 탭이 백그라운드에 있어도 연결 유지
  })
}

// Monitoring API
export interface UsageStats {
  period_hours: number
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  total_cost_usd: number
  avg_latency_ms: number
  cache_hits: number
  cache_hit_rate: number
}

export interface CostSummary {
  daily: {
    cost_usd: number
    limit_usd: number
    remaining_usd: number
    usage_percent: number
  }
  monthly: {
    cost_usd: number
    limit_usd: number
    remaining_usd: number
    usage_percent: number
    year: number
    month: number
  }
  cache: {
    hit_rate_24h: number
    hit_rate_percent: number
  }
}

export interface CacheStats {
  status: string
  total_entries?: number
  active_entries?: number
  expired_entries?: number
  avg_hit_count?: number
  error?: string
}

export interface UsageLogEntry {
  id: number
  model: string
  model_version: string
  request_type: string
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost_usd: number
  cached: boolean
  latency_ms: number
  created_at: string
}

export interface UsageHistory {
  results: UsageLogEntry[]
  pagination: {
    current_page: number
    page_size: number
    total_pages: number
    total_count: number
    has_next: boolean
    has_previous: boolean
  }
}

export interface ModelPricing {
  model: string
  name: string
  input_per_1m_tokens: number
  output_per_1m_tokens: number
}

export const monitoringService = {
  async getUsageStats(hours: number = 24, userOnly: boolean = true): Promise<UsageStats> {
    const response = await api.get('/rag/monitoring/usage/', {
      params: { hours, user_only: userOnly }
    })
    return response.data
  },

  async getCostSummary(): Promise<CostSummary> {
    const response = await api.get('/rag/monitoring/cost/')
    return response.data
  },

  async getCacheStats(): Promise<CacheStats> {
    const response = await api.get('/rag/monitoring/cache/')
    return response.data
  },

  async getUsageHistory(
    page: number = 1,
    pageSize: number = 20,
    hours: number = 168
  ): Promise<UsageHistory> {
    const response = await api.get('/rag/monitoring/history/', {
      params: { page, page_size: pageSize, hours }
    })
    return response.data
  },

  async getModelPricing(): Promise<{ pricing: ModelPricing[]; currency: string; unit: string; last_updated: string }> {
    const response = await api.get('/rag/monitoring/pricing/')
    return response.data
  },
}
