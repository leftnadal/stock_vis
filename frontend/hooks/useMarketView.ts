/**
 * Market View TanStack Query hooks
 */

import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import {
  fetchSeeds,
  fetchSectorGraph,
  fetchNeighbors,
  fetchSignals,
  fetchEgo,
  fetchCentralityTop,
} from '@/services/chainsightService';
import type {
  SeedResponse,
  SectorGraphResponse,
  NeighborResponse,
  SignalFeedResponse,
  EgoGraphResponse,
  CentralityTopResponse,
} from '@/types/chainsight';

const STALE_30M = 1000 * 60 * 30;
const STALE_5M = 1000 * 60 * 5;
const GC_TIME = 1000 * 60 * 60;

export const MARKET_VIEW_KEYS = {
  seeds: ['chainsight', 'seeds'] as const,
  sectorGraph: (sector: string) => ['chainsight', 'sectorGraph', sector] as const,
  neighbors: (symbol: string) => ['chainsight', 'neighbors', symbol] as const,
  ego: (symbol: string) => ['chainsight', 'ego', symbol] as const,
  signals: (sector?: string) => ['chainsight', 'signals', sector ?? 'all'] as const,
  centralityTop: (metric: string, n: number) =>
    ['chainsight', 'centralityTop', metric, n] as const,
};

export function useSeedData() {
  return useQuery<SeedResponse>({
    queryKey: MARKET_VIEW_KEYS.seeds,
    queryFn: fetchSeeds,
    staleTime: STALE_30M,
    gcTime: GC_TIME,
  });
}

export function useSectorGraph(sector: string | null) {
  return useQuery<SectorGraphResponse>({
    queryKey: MARKET_VIEW_KEYS.sectorGraph(sector ?? ''),
    queryFn: () => fetchSectorGraph(sector!, 12),
    staleTime: STALE_30M,
    gcTime: GC_TIME,
    enabled: !!sector,
    // ⑳-E: localhost API. onlineManager 오프라인 오판 시 재시도가 'paused' 로 멈춰
    // 503 이 isError 로 표면화되지 못하고 sector-unavailable 이 미발화한다(라이브 실증).
    // networkMode 'always'(초기 페치 pause 차단) + retry false(재시도 pause 경로 자체 제거,
    // 첫 실패를 즉시 error 확정 → GraphStatePanel 재시도 버튼으로 사용자 재시도).
    networkMode: 'always',
    retry: false,
  });
}

export function useNeighbors(symbol: string | null) {
  return useQuery<NeighborResponse>({
    queryKey: MARKET_VIEW_KEYS.neighbors(symbol ?? ''),
    queryFn: () => fetchNeighbors(symbol!, 8),
    staleTime: STALE_5M,
    gcTime: GC_TIME,
    enabled: !!symbol,
  });
}

export function useEgo(symbol: string | null) {
  return useQuery<EgoGraphResponse>({
    queryKey: MARKET_VIEW_KEYS.ego(symbol ?? ''),
    queryFn: () => fetchEgo(symbol!),
    staleTime: STALE_5M,
    gcTime: GC_TIME,
    enabled: !!symbol,
    // ⑳-E: pause 없이 실패를 error 로 확정 → load-error 상태 신뢰성 확보(useSectorGraph 동일).
    networkMode: 'always',
    retry: false,
  });
}

export function useCentralityTop(metric: string, n: number) {
  return useQuery<CentralityTopResponse>({
    queryKey: MARKET_VIEW_KEYS.centralityTop(metric, n),
    queryFn: () => fetchCentralityTop({ metric, n }),
    staleTime: STALE_30M,
    gcTime: GC_TIME,
  });
}

export function useSignalFeed(sector?: string) {
  return useInfiniteQuery<SignalFeedResponse, Error, { pages: SignalFeedResponse[] }, readonly string[], number>({
    queryKey: MARKET_VIEW_KEYS.signals(sector),
    queryFn: ({ pageParam }) => fetchSignals(pageParam, 5, sector),
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.has_next ? lastPage.page + 1 : undefined,
    staleTime: STALE_30M,
    gcTime: GC_TIME,
  });
}
