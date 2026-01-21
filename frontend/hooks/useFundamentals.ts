import { useQuery } from '@tanstack/react-query';
import { stockService } from '@/services/stock';
import type { AllFundamentals } from '@/types/fundamentals';

// Query keys for fundamentals
export const FUNDAMENTALS_QUERY_KEYS = {
  all: (symbol: string) => ['fundamentals', symbol] as const,
  keyMetrics: (symbol: string, period: 'annual' | 'quarterly') =>
    ['fundamentals', 'key-metrics', symbol, period] as const,
  ratios: (symbol: string, period: 'annual' | 'quarterly') =>
    ['fundamentals', 'ratios', symbol, period] as const,
  dcf: (symbol: string) => ['fundamentals', 'dcf', symbol] as const,
  rating: (symbol: string) => ['fundamentals', 'rating', symbol] as const,
};

// Hook to fetch all fundamentals data
export function useFundamentals(symbol: string) {
  return useQuery<AllFundamentals>({
    queryKey: FUNDAMENTALS_QUERY_KEYS.all(symbol),
    queryFn: () => stockService.getAllFundamentals(symbol),
    staleTime: 1000 * 60 * 10, // 10 minutes
    enabled: !!symbol,
  });
}

// Hook to fetch key metrics only
export function useKeyMetrics(
  symbol: string,
  period: 'annual' | 'quarterly' = 'annual',
  limit: number = 5
) {
  return useQuery({
    queryKey: FUNDAMENTALS_QUERY_KEYS.keyMetrics(symbol, period),
    queryFn: () => stockService.getKeyMetrics(symbol, period, limit),
    staleTime: 1000 * 60 * 10, // 10 minutes
    enabled: !!symbol,
  });
}

// Hook to fetch financial ratios only
export function useFinancialRatios(
  symbol: string,
  period: 'annual' | 'quarterly' = 'annual',
  limit: number = 5
) {
  return useQuery({
    queryKey: FUNDAMENTALS_QUERY_KEYS.ratios(symbol, period),
    queryFn: () => stockService.getFinancialRatios(symbol, period, limit),
    staleTime: 1000 * 60 * 10, // 10 minutes
    enabled: !!symbol,
  });
}

// Hook to fetch DCF valuation only
export function useDCF(symbol: string) {
  return useQuery({
    queryKey: FUNDAMENTALS_QUERY_KEYS.dcf(symbol),
    queryFn: () => stockService.getDCF(symbol),
    staleTime: 1000 * 60 * 10, // 10 minutes
    enabled: !!symbol,
  });
}

// Hook to fetch investment rating only
export function useRating(symbol: string) {
  return useQuery({
    queryKey: FUNDAMENTALS_QUERY_KEYS.rating(symbol),
    queryFn: () => stockService.getRating(symbol),
    staleTime: 1000 * 60 * 10, // 10 minutes
    enabled: !!symbol,
  });
}
