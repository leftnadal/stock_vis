import axios from 'axios';
import type {
  AdminOverviewResponse,
  AdminStocksStatus,
  AdminScreenerStatus,
  AdminMarketPulseStatus,
  AdminNewsStatus,
  AdminSystemStatus,
  TaskLogEntry,
  TaskLogParams,
  HealthCheckResponse,
  ProviderStatusResponse,
  AdminActionsResponse,
  AdminActionRequest,
  AdminActionResponse,
  AdminTaskStatus,
  NewsCollectionCategory,
  NewsCategoryCreateRequest,
  NewsCategoryUpdateRequest,
  SectorOptionsResponse,
} from '@/types/admin';

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
      console.error('[Admin] Network error');
    } else if (error.response.status !== 429) {
      // 429(쿨다운)은 예상된 응답이므로 에러 로깅 제외
      console.error(`[Admin] Error ${error.response.status}:`, error.response.data);
    }
    return Promise.reject(error);
  }
);

export const adminService = {
  // 신규 Admin Dashboard 엔드포인트
  getOverview: (): Promise<AdminOverviewResponse> =>
    api.get('/serverless/admin/dashboard/overview/').then((r) => r.data),

  getStocksStatus: (): Promise<AdminStocksStatus> =>
    api.get('/serverless/admin/dashboard/stocks/').then((r) => r.data),

  getScreenerStatus: (): Promise<AdminScreenerStatus> =>
    api.get('/serverless/admin/dashboard/screener/').then((r) => r.data),

  getMarketPulseStatus: (): Promise<AdminMarketPulseStatus> =>
    api.get('/serverless/admin/dashboard/market-pulse/').then((r) => r.data),

  getNewsStatus: (): Promise<AdminNewsStatus> =>
    api.get('/serverless/admin/dashboard/news/').then((r) => r.data),

  getSystemStatus: (): Promise<AdminSystemStatus> =>
    api.get('/serverless/admin/dashboard/system/').then((r) => r.data),

  getTaskLogs: (params?: TaskLogParams): Promise<TaskLogEntry[]> =>
    api.get('/serverless/admin/dashboard/tasks/', { params }).then((r) => r.data),

  // Admin Actions
  getAvailableActions: (): Promise<AdminActionsResponse> =>
    api.get('/serverless/admin/dashboard/actions/').then((r) => r.data),

  executeAction: (req: AdminActionRequest): Promise<AdminActionResponse> =>
    api.post('/serverless/admin/dashboard/actions/', req).then((r) => r.data),

  getTaskStatus: (taskId: string): Promise<AdminTaskStatus> =>
    api.get(`/serverless/admin/dashboard/actions/status/${taskId}/`).then((r) => r.data),

  // News Collection Categories
  getNewsCategories: (): Promise<{ categories: NewsCollectionCategory[] }> =>
    api.get('/serverless/admin/dashboard/news/categories/').then((r) => r.data),

  createNewsCategory: (data: NewsCategoryCreateRequest): Promise<NewsCollectionCategory> =>
    api.post('/serverless/admin/dashboard/news/categories/', data).then((r) => r.data),

  updateNewsCategory: (id: number, data: NewsCategoryUpdateRequest): Promise<NewsCollectionCategory> =>
    api.put(`/serverless/admin/dashboard/news/categories/${id}/`, data).then((r) => r.data),

  deleteNewsCategory: (id: number): Promise<void> =>
    api.delete(`/serverless/admin/dashboard/news/categories/${id}/`).then(() => undefined),

  getSectorOptions: (): Promise<SectorOptionsResponse> =>
    api.get('/serverless/admin/dashboard/news/sector-options/').then((r) => r.data),

  // 기존 엔드포인트 재사용
  getHealthCheck: (): Promise<HealthCheckResponse> =>
    api.get('/health/').then((r) => r.data),

  getProviderStatus: (): Promise<ProviderStatusResponse> =>
    api.get('/admin/providers/status/').then((r) => r.data),
};
