import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { keywordService } from '@/services/keywordService';
import type {
  KeywordAPIResponse,
  BatchKeywordsRequest,
  BatchKeywordsResponse,
} from '@/types/keyword';

const QUERY_KEYS = {
  keywords: (symbol: string, date?: string) => ['keywords', symbol.toUpperCase(), date] as const,
  batchKeywords: (symbols: string[], date?: string) =>
    ['keywords-batch', symbols.map((s) => s.toUpperCase()).sort(), date] as const,
  allKeywords: ['keywords'] as const,
} as const;

/**
 * 단일 종목 키워드 조회 훅
 */
export function useKeywords(symbol: string, date?: string) {
  return useQuery<KeywordAPIResponse>({
    queryKey: QUERY_KEYS.keywords(symbol, date),
    queryFn: () => keywordService.getKeywords(symbol, date),
    staleTime: 10 * 60 * 1000, // 10분 (LLM 생성 데이터는 자주 변경되지 않음)
    enabled: !!symbol, // symbol이 있을 때만 실행
  });
}

/**
 * 여러 종목 키워드 일괄 조회 훅
 */
export function useBatchKeywords(symbols: string[], date?: string) {
  return useQuery<BatchKeywordsResponse>({
    queryKey: QUERY_KEYS.batchKeywords(symbols, date),
    queryFn: () => keywordService.getBatchKeywords({ symbols, date }),
    staleTime: 10 * 60 * 1000,
    enabled: symbols.length > 0,
  });
}

/**
 * 키워드 재생성 mutation 훅
 */
export function useRegenerateKeywords() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ symbol, date }: { symbol: string; date?: string }) =>
      keywordService.regenerateKeywords(symbol, date),
    onSuccess: (data, variables) => {
      // 해당 종목의 키워드 쿼리 무효화
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.keywords(variables.symbol, variables.date),
      });
      // 배치 쿼리도 무효화 (해당 종목이 포함된 경우)
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.allKeywords,
      });
    },
  });
}

/**
 * Market Movers 전체 키워드 생성 mutation 훅
 */
export function useGenerateAllKeywords() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ type, date }: { type: 'gainers' | 'losers' | 'actives'; date?: string }) =>
      keywordService.generateAllKeywords(type, date),
    onSuccess: () => {
      // 모든 키워드 쿼리 무효화
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.allKeywords });
    },
  });
}
