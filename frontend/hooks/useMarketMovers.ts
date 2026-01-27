import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { serverlessService } from '@/services/serverlessService';
import { keywordService } from '@/services/keywordService';
import type { ServerlessMarketMoversResponse, MoverType } from '@/types/market';

const QUERY_KEYS = {
  marketMovers: (type: MoverType, date?: string) => ['market-movers', type, date] as const,
  allMarketMovers: ['market-movers'] as const,
  keywords: ['keywords'] as const,
} as const;

export function useMarketMovers(type: MoverType = 'gainers', date?: string) {
  return useQuery<ServerlessMarketMoversResponse>({
    queryKey: QUERY_KEYS.marketMovers(type, date),
    queryFn: () => serverlessService.getMarketMovers(type, date),
    staleTime: 5 * 60 * 1000, // 5분
    refetchInterval: 5 * 60 * 1000, // 5분마다 자동 갱신
  });
}

export function useSyncMarketMovers() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (date?: string) => serverlessService.syncNow(date),
    onSuccess: () => {
      // 모든 market-movers 쿼리 무효화하여 자동 리페치
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.allMarketMovers });
    },
  });
}

export function useGenerateKeywords() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ type, date }: { type: MoverType; date?: string }) =>
      keywordService.generateAllKeywords(type, date),
    onSuccess: () => {
      // 키워드 쿼리 무효화 (생성 완료 후 리페치)
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.keywords });
      // Market Movers도 무효화 (키워드 포함 응답)
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.allMarketMovers });
    },
  });
}
