import { useQuery } from '@tanstack/react-query';
import { screenerService } from '@/services/screenerService';
import type { MarketBreadthResponse } from '@/types/screener';

const QUERY_KEYS = {
  marketBreadth: (date?: string) => ['market-breadth', date] as const,
  allMarketBreadth: ['market-breadth'] as const,
} as const;

export function useMarketBreadth(date?: string) {
  return useQuery<MarketBreadthResponse>({
    queryKey: QUERY_KEYS.marketBreadth(date),
    queryFn: () => screenerService.getMarketBreadth(date),
    staleTime: 5 * 60 * 1000, // 5분
    refetchInterval: 5 * 60 * 1000, // 5분마다 자동 갱신
  });
}
