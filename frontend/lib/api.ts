// API 클라이언트 설정

import axios from 'axios';
import { StockListResponse, StockDetailResponse, RAGContext } from '@/types/stock';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API 함수들
export const stockAPI = {
  // MVP 주식 목록
  getStocks: async (params?: {
    mode?: 'summary' | 'full';
    sector?: string;
    search?: string
  }): Promise<StockListResponse> => {
    const response = await apiClient.get('/stocks/api/mvp/stocks/', { params });
    return response.data;
  },

  // MVP 주식 상세
  getStockDetail: async (
    symbol: string,
    mode: 'summary' | 'full' = 'summary'
  ): Promise<StockDetailResponse> => {
    const response = await apiClient.get(`/stocks/api/mvp/stock/${symbol}/`, {
      params: { mode }
    });
    return response.data;
  },

  // RAG 컨텍스트
  getRAGContext: async (
    symbol: string,
    mode: 'summary' | 'full' = 'summary'
  ): Promise<RAGContext> => {
    const response = await apiClient.get(`/stocks/api/mvp/rag/${symbol}/`, {
      params: { mode }
    });
    return response.data;
  },

  // 섹터 목록
  getSectors: async (): Promise<{ sectors: string[] }> => {
    const response = await apiClient.get('/stocks/api/mvp/sectors/');
    return response.data;
  },
};

export default apiClient;