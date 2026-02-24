/**
 * Chain Sight Stock 서비스
 *
 * 개별 종목 페이지에서 AI 가이드와 함께하는 주식 탐험 기능
 */
import axios from 'axios';
import type {
  ChainSightCategoriesResponse,
  ChainSightCategoryStocksResponse,
  ChainSightSyncResponse,
} from '@/types/chainSight';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export const chainSightService = {
  /**
   * 종목의 카테고리 조회
   *
   * @param symbol - 종목 심볼 (예: NVDA)
   * @returns 카테고리 목록
   *
   * @example
   * const { data } = await chainSightService.getCategories('NVDA');
   * console.log(data.categories);
   * // [{ id: 'peer', name: '경쟁사', tier: 0, count: 5, icon: '⚔️' }, ...]
   */
  async getCategories(symbol: string): Promise<ChainSightCategoriesResponse> {
    const response = await api.get<ChainSightCategoriesResponse>(
      `/serverless/chain-sight/stock/${symbol.toUpperCase()}`
    );
    return response.data;
  },

  /**
   * 카테고리별 종목 조회
   *
   * @param symbol - 원본 종목 심볼
   * @param categoryId - 카테고리 ID (peer, same_industry, co_mentioned, ai_ecosystem 등)
   * @param limit - 최대 반환 개수 (기본값: 10)
   * @returns 관련 종목 목록 + AI 인사이트
   *
   * @example
   * const { data } = await chainSightService.getCategoryStocks('NVDA', 'peer');
   * console.log(data.stocks);
   * // [{ symbol: 'AMD', company_name: 'Advanced Micro Devices', ... }]
   */
  async getCategoryStocks(
    symbol: string,
    categoryId: string,
    limit: number = 10
  ): Promise<ChainSightCategoryStocksResponse> {
    const response = await api.get<ChainSightCategoryStocksResponse>(
      `/serverless/chain-sight/stock/${symbol.toUpperCase()}/category/${categoryId}`,
      { params: { limit } }
    );
    return response.data;
  },

  /**
   * 종목 관계 동기화 트리거
   *
   * Cold Start 시 또는 수동 새로고침 시 사용
   *
   * @param symbol - 종목 심볼
   * @returns 동기화 결과
   */
  async syncRelationships(symbol: string): Promise<ChainSightSyncResponse> {
    const response = await api.post<ChainSightSyncResponse>(
      `/serverless/chain-sight/stock/${symbol.toUpperCase()}/sync`
    );
    return response.data;
  },

  /**
   * 사용자 행동 트래킹 (Phase 6)
   *
   * 카드 클릭, 카테고리 클릭, 파도타기 등의 행동을 기록하여
   * edge weight를 강화합니다. fire-and-forget으로 호출합니다.
   *
   * @param symbol - 원본 종목 심볼
   * @param action - 행동 타입 ('card_click', 'category_click', 'navigate')
   * @param targetSymbol - 대상 종목 심볼
   */
  async trackInteraction(symbol: string, action: string, targetSymbol: string): Promise<void> {
    await api.post(`/serverless/chain-sight/stock/${symbol.toUpperCase()}/track`, {
      action,
      target_symbol: targetSymbol,
    });
  },
};

export default chainSightService;
