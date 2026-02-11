/**
 * ETF 수집 상태 관리 훅
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ETFCollectionStatusResponse,
  ETFSyncResponse,
  ETFProfile,
} from '@/types/etf';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

/**
 * ETF 수집 상태 조회 훅
 */
export function useETFCollectionStatus(tier?: 'sector' | 'theme') {
  return useQuery<ETFCollectionStatusResponse>({
    queryKey: ['etf-collection-status', tier],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (tier) params.append('tier', tier);

      const url = `${API_BASE}/serverless/etf/status${params.toString() ? '?' + params.toString() : ''}`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error('ETF 상태 조회 실패');
      }

      return response.json();
    },
    staleTime: 30 * 1000, // 30초
    refetchOnWindowFocus: false,
  });
}

/**
 * 단일 ETF 동기화 훅
 */
export function useETFSync() {
  const queryClient = useQueryClient();

  return useMutation<ETFSyncResponse, Error, string | undefined>({
    mutationFn: async (etfSymbol?: string) => {
      const body = etfSymbol ? { etf_symbol: etfSymbol } : {};

      const response = await fetch(`${API_BASE}/serverless/etf/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error('ETF 동기화 실패');
      }

      return response.json();
    },
    onSuccess: () => {
      // 상태 쿼리 무효화
      queryClient.invalidateQueries({ queryKey: ['etf-collection-status'] });
      // 테마 목록도 무효화
      queryClient.invalidateQueries({ queryKey: ['themes'] });
    },
  });
}

/**
 * 테마 매치 갱신 훅
 */
export function useRefreshThemeMatches() {
  const queryClient = useQueryClient();

  return useMutation<{ success: boolean; data: { created: number; updated: number; total: number } }, Error>({
    mutationFn: async () => {
      const response = await fetch(`${API_BASE}/serverless/themes/refresh`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('테마 매치 갱신 실패');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['themes'] });
      queryClient.invalidateQueries({ queryKey: ['chain-sight'] });
    },
  });
}

/**
 * URL 복구 응답 타입
 */
interface URLResolveResult {
  etf: string;
  status: 'resolved' | 'failed';
  old_url?: string;
  new_url?: string;
  error?: string;
}

interface URLResolveResponse {
  success: boolean;
  data: {
    results: URLResolveResult[];
    summary: {
      total: number;
      resolved: number;
      failed: number;
    };
  };
}

/**
 * ETF CSV URL 자동 복구 훅
 *
 * 404 에러가 발생한 ETF의 CSV URL을 자동으로 찾아 업데이트합니다.
 */
export function useResolveETFUrl() {
  const queryClient = useQueryClient();

  return useMutation<URLResolveResponse, Error, string | undefined>({
    mutationFn: async (etfSymbol?: string) => {
      const body = etfSymbol ? { etf_symbol: etfSymbol } : {};

      const response = await fetch(`${API_BASE}/serverless/etf/resolve-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error('URL 복구 실패');
      }

      return response.json();
    },
    onSuccess: () => {
      // 상태 쿼리 무효화
      queryClient.invalidateQueries({ queryKey: ['etf-collection-status'] });
    },
  });
}

// 쿼리 키 상수
export const etfQueryKeys = {
  status: (tier?: string) => ['etf-collection-status', tier] as const,
  holdings: (etfSymbol: string) => ['etf-holdings', etfSymbol] as const,
  themes: () => ['themes'] as const,
  stockThemes: (symbol: string) => ['stock-themes', symbol] as const,
  etfPeers: (symbol: string) => ['etf-peers', symbol] as const,
};
