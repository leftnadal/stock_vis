/**
 * useChainSightCategories Hook
 *
 * 종목의 Chain Sight 카테고리를 조회합니다.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chainSightService } from '@/services/chainSightService';
import type { ChainSightCategoriesResponse } from '@/types/chainSight';

const QUERY_KEYS = {
  categories: (symbol: string) => ['chain-sight', 'categories', symbol.toUpperCase()] as const,
} as const;

/**
 * 종목의 카테고리 조회 훅
 *
 * @param symbol - 종목 심볼
 * @param options - 추가 옵션
 *
 * @example
 * const { data, isLoading, isColdStart } = useChainSightCategories('NVDA');
 */
export function useChainSightCategories(
  symbol: string,
  options?: {
    enabled?: boolean;
  }
) {
  const query = useQuery<ChainSightCategoriesResponse>({
    queryKey: QUERY_KEYS.categories(symbol),
    queryFn: () => chainSightService.getCategories(symbol),
    enabled: options?.enabled !== false && !!symbol,
    staleTime: 5 * 60 * 1000, // 5분
    refetchOnWindowFocus: false,
  });

  return {
    ...query,
    categories: query.data?.data?.categories || [],
    companyName: query.data?.data?.company_name,
    isColdStart: query.data?.data?.is_cold_start || false,
  };
}

/**
 * 관계 동기화 뮤테이션 훅
 *
 * Cold Start 시 또는 수동 새로고침 시 사용
 *
 * @example
 * const { mutate: sync, isPending } = useChainSightSync('NVDA');
 * sync(); // 동기화 시작
 */
export function useChainSightSync(symbol: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => chainSightService.syncRelationships(symbol),
    onSuccess: () => {
      // 카테고리 쿼리 무효화
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.categories(symbol),
      });
    },
  });
}

export { QUERY_KEYS as CHAIN_SIGHT_QUERY_KEYS };
