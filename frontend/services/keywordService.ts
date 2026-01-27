import axios from 'axios';
import type {
  KeywordAPIResponse,
  BatchKeywordsRequest,
  BatchKeywordsResponse,
} from '@/types/keyword';

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

export const keywordService = {
  /**
   * 단일 종목의 LLM 키워드 조회
   * @param symbol - 종목 심볼
   * @param date - 조회 날짜 (YYYY-MM-DD, 선택사항)
   */
  async getKeywords(symbol: string, date?: string): Promise<KeywordAPIResponse> {
    const params: Record<string, string> = {};
    if (date) {
      params.date = date;
    }

    const response = await api.get(`/serverless/keywords/${symbol.toUpperCase()}`, {
      params,
    });
    return response.data;
  },

  /**
   * 여러 종목의 LLM 키워드 일괄 조회
   * @param request - 종목 심볼 배열 + 날짜 (선택)
   */
  async getBatchKeywords(request: BatchKeywordsRequest): Promise<BatchKeywordsResponse> {
    const response = await api.post('/serverless/keywords/batch', request);
    return response.data;
  },

  /**
   * 특정 종목의 키워드 재생성 트리거 (관리자용)
   * @param symbol - 종목 심볼
   * @param date - 날짜 (선택)
   */
  async regenerateKeywords(symbol: string, date?: string): Promise<KeywordAPIResponse> {
    const response = await api.post(`/serverless/keywords/${symbol.toUpperCase()}/regenerate`, {
      date,
    });
    return response.data;
  },

  /**
   * Market Movers 전체 키워드 일괄 생성 (Celery 비동기)
   * @param type - 'gainers' | 'losers' | 'actives'
   * @param date - 날짜 (선택)
   */
  async generateAllKeywords(type: 'gainers' | 'losers' | 'actives', date?: string) {
    const response = await api.post('/serverless/keywords/generate-all', { type, date });
    return response.data;
  },

  /**
   * 스크리너 종목들의 키워드 일괄 생성 (Celery 비동기)
   * @param stocks - 종목 정보 배열
   */
  async generateScreenerKeywords(
    stocks: Array<{
      symbol: string;
      company_name?: string;
      sector?: string;
      industry?: string;
      change_percent?: number;
    }>
  ) {
    const response = await api.post('/serverless/keywords/generate-screener', { stocks });
    return response.data;
  },
};
