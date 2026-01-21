import { useQuery } from '@tanstack/react-query';
import { strategyService, type MajorIndex } from '@/services/strategyService';

const QUERY_KEYS = {
  majorIndices: ['exchange-quotes', 'major-indices'] as const,
};

export function useExchangeQuotes() {
  return useQuery<MajorIndex[], Error>({
    queryKey: QUERY_KEYS.majorIndices,
    queryFn: () => strategyService.getMajorIndices(),
    staleTime: 1000 * 60, // 60초
    refetchInterval: 1000 * 60, // 60초마다 폴링
    refetchOnWindowFocus: true,
  });
}
