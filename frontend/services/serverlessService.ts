import axios from 'axios';
import type { ServerlessMarketMoversResponse, MoverType } from '@/types/market';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const serverlessService = {
  /**
   * Market Movers 데이터 조회
   * @param type - 'gainers' | 'losers' | 'actives'
   * @param date - 조회 날짜 (YYYY-MM-DD, 선택사항)
   */
  async getMarketMovers(
    type: MoverType = 'gainers',
    date?: string
  ): Promise<ServerlessMarketMoversResponse> {
    const params: Record<string, string> = { type };
    if (date) {
      params.date = date;
    }

    const response = await api.get('/serverless/movers', { params });
    return response.data;
  },

  /**
   * 특정 종목의 Market Mover 상세 정보
   * @param symbol - 종목 심볼
   * @param date - 조회 날짜 (YYYY-MM-DD, 선택사항)
   */
  async getMarketMoverDetail(symbol: string, date?: string) {
    const params: Record<string, string> = {};
    if (date) {
      params.date = date;
    }

    const response = await api.get(`/serverless/movers/${symbol.toUpperCase()}`, { params });
    return response.data;
  },

  /**
   * Market Movers 동기화 트리거 (관리자용, Celery 비동기)
   * @param date - 동기화 날짜 (선택사항)
   */
  async triggerSync(date?: string) {
    const response = await api.post('/serverless/sync', { date });
    return response.data;
  },

  /**
   * Market Movers 즉시 동기화 (Celery 없이 동기 실행)
   * @param date - 동기화 날짜 (선택사항)
   */
  async syncNow(date?: string): Promise<{
    success: boolean;
    data?: {
      message: string;
      date: string;
      results: { gainers: number; losers: number; actives: number; errors: number };
    };
    error?: { code: string; message: string };
  }> {
    const response = await api.post('/serverless/sync-now', { date });
    return response.data;
  },

  /**
   * 헬스체크
   */
  async healthCheck() {
    const response = await api.get('/serverless/health');
    return response.data;
  },
};
