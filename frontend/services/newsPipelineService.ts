import axios from 'axios';
import type {
  CollectionLogsResponse,
  PipelineHealthResponse,
  MLTrendResponse,
  LLMUsageResponse,
} from '@/types/newsPipeline';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - JWT 토큰 추가
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - 에러 처리
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      console.error('[NewsPipeline] Network error');
    } else if (error.response.status !== 429) {
      // 429(쿨다운)은 예상된 응답이므로 에러 로깅 제외
      console.error(`[NewsPipeline] Error ${error.response.status}:`, error.response.data);
    }
    return Promise.reject(error);
  }
);

export const newsPipelineService = {
  getCollectionLogs: (days?: number, provider?: string): Promise<CollectionLogsResponse> => {
    const params: Record<string, string | number> = {};
    if (days !== undefined) params.days = days;
    if (provider) params.provider = provider;
    return api.get('/news/collection-logs/', { params }).then((r) => r.data);
  },

  getPipelineHealth: (forceRefresh?: boolean): Promise<PipelineHealthResponse> => {
    const params: Record<string, string> = {};
    if (forceRefresh) params.force_refresh = 'true';
    return api.get('/news/pipeline-health/', { params }).then((r) => r.data);
  },

  getMLTrend: (weeks?: number): Promise<MLTrendResponse> => {
    const params: Record<string, number> = {};
    if (weeks !== undefined) params.weeks = weeks;
    return api.get('/news/ml-trend/', { params }).then((r) => r.data);
  },

  getLLMUsage: (days?: number): Promise<LLMUsageResponse> => {
    const params: Record<string, number> = {};
    if (days !== undefined) params.days = days;
    return api.get('/news/llm-usage/', { params }).then((r) => r.data);
  },
};
