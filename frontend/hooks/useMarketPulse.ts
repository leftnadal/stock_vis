import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import { macroService } from '@/services/macroService';
import type { MarketPulseDashboard } from '@/types/macro';

const STORAGE_KEY = 'market-pulse-cache';
const CACHE_MAX_AGE = 30 * 60 * 1000; // 30분

/**
 * localStorage에서 캐시된 데이터 로드
 */
function loadCachedData(): MarketPulseDashboard | undefined {
  if (typeof window === 'undefined') return undefined;

  try {
    const cached = localStorage.getItem(STORAGE_KEY);
    if (!cached) return undefined;

    const { data, timestamp } = JSON.parse(cached);
    if (Date.now() - timestamp > CACHE_MAX_AGE) {
      localStorage.removeItem(STORAGE_KEY);
      return undefined;
    }
    return data;
  } catch {
    return undefined;
  }
}

/**
 * localStorage에 데이터 캐시
 */
function saveCachedData(data: MarketPulseDashboard): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      data,
      timestamp: Date.now(),
    }));
  } catch {
    // localStorage full - ignore
  }
}

/**
 * Market Pulse 데이터 조회 훅
 * - localStorage 캐시로 즉시 표시 (클라이언트에서만)
 * - 백그라운드 리페치로 최신 데이터 갱신
 */
export function useMarketPulse() {
  // Hydration 이후에만 localStorage 캐시 사용
  const [mounted, setMounted] = useState(false);
  const [cachedData, setCachedData] = useState<MarketPulseDashboard | undefined>(undefined);

  useEffect(() => {
    setMounted(true);
    const cached = loadCachedData();
    if (cached) {
      setCachedData(cached);
    }
  }, []);

  const query = useQuery<MarketPulseDashboard>({
    queryKey: ['market-pulse'],
    queryFn: () => macroService.getMarketPulse(),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchInterval: 60 * 1000,
    // placeholderData로 캐시 데이터 사용 (hydration 이후에만)
    placeholderData: mounted ? cachedData : undefined,
  });

  // 새 데이터가 로드되면 localStorage에 저장
  useEffect(() => {
    if (query.data && mounted) {
      saveCachedData(query.data);
    }
  }, [query.data, mounted]);

  return {
    ...query,
    // 캐시 데이터가 있으면 로딩 중에도 표시
    data: query.data || (mounted ? cachedData : undefined),
    // 실제 로딩 상태 (캐시 있으면 로딩 아님)
    isLoading: query.isLoading && !cachedData,
  };
}

/**
 * 데이터가 비어있는지 확인
 */
export function isMarketPulseDataEmpty(data: MarketPulseDashboard | undefined): boolean {
  if (!data) return true;

  const indices = data.global_markets?.indices;
  if (indices) {
    const hasIndexData = indices.sp500 || indices.nasdaq || indices.dow || indices.russell2000;
    if (!hasIndexData) return true;
  }

  return false;
}

/**
 * 데이터 동기화 상태 폴링 훅
 */
export function useSyncStatus(enabled: boolean) {
  return useQuery({
    queryKey: ['sync-status'],
    queryFn: () => macroService.getSyncStatus(),
    enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === 'running' ? 2000 : false;
    },
  });
}

/**
 * 데이터 동기화 시작 mutation
 */
export function useStartDataSync() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => macroService.startDataSync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sync-status'] });
    },
  });
}

/**
 * 동기화 완료 시 데이터 리페치
 */
export function useRefreshOnSyncComplete() {
  const queryClient = useQueryClient();

  const invalidateMarketPulse = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['market-pulse'] });
  }, [queryClient]);

  return { invalidateMarketPulse };
}
