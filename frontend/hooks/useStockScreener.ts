import { useQuery } from '@tanstack/react-query';
import { strategyService, type ScreenerStock, type ScreenerFilters } from '@/services/strategyService';

const QUERY_KEYS = {
  screener: (filters?: ScreenerFilters) => ['stock-screener', filters] as const,
  largeCapStocks: ['stock-screener', 'large-cap'] as const,
};

export function useStockScreener(filters?: ScreenerFilters) {
  // 필터를 문자열로 변환하여 queryKey에 사용 (객체 비교 문제 방지)
  const filterKey = JSON.stringify(filters || {});

  return useQuery<ScreenerStock[], Error>({
    queryKey: ['stock-screener', filterKey],
    queryFn: () => strategyService.getScreenerResults(filters),
    staleTime: 0, // 항상 새로 요청
    refetchOnWindowFocus: false,
  });
}

export function useLargeCapStocks() {
  return useQuery<ScreenerStock[], Error>({
    queryKey: QUERY_KEYS.largeCapStocks,
    queryFn: () => strategyService.getLargeCapStocks(),
    staleTime: 1000 * 60 * 5, // 300초 (5분)
    refetchOnWindowFocus: false,
  });
}
