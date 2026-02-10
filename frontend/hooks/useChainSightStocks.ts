/**
 * useChainSightStocks Hook
 *
 * 카테고리별 관련 종목을 조회합니다.
 */
import { useQuery } from '@tanstack/react-query';
import { chainSightService } from '@/services/chainSightService';
import type { ChainSightCategoryStocksResponse } from '@/types/chainSight';

const QUERY_KEYS = {
  categoryStocks: (symbol: string, categoryId: string | null) =>
    ['chain-sight', 'stocks', symbol.toUpperCase(), categoryId] as const,
} as const;

/**
 * 카테고리별 종목 조회 훅
 *
 * @param symbol - 원본 종목 심볼
 * @param categoryId - 카테고리 ID (null이면 비활성화)
 * @param limit - 최대 반환 개수
 *
 * @example
 * const { data, isLoading } = useChainSightStocks('NVDA', 'peer');
 */
export function useChainSightStocks(
  symbol: string,
  categoryId: string | null,
  limit: number = 10
) {
  const query = useQuery<ChainSightCategoryStocksResponse>({
    queryKey: QUERY_KEYS.categoryStocks(symbol, categoryId),
    queryFn: () => chainSightService.getCategoryStocks(symbol, categoryId!, limit),
    enabled: !!symbol && !!categoryId,
    staleTime: 5 * 60 * 1000, // 5분
    refetchOnWindowFocus: false,
  });

  return {
    ...query,
    stocks: query.data?.data?.stocks || [],
    category: query.data?.data?.category,
    aiInsights: query.data?.data?.ai_insights,
    followUpQuestions: query.data?.data?.follow_up_questions || [],
  };
}

export { QUERY_KEYS as CHAIN_SIGHT_STOCKS_QUERY_KEYS };
