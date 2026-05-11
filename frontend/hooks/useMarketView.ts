/**
 * Market View TanStack Query hooks
 */

import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import {
  fetchSeeds,
  fetchSectorGraph,
  fetchNeighbors,
  fetchSignals,
} from '@/services/chainsightService';
import type {
  SeedResponse,
  SectorGraphResponse,
  NeighborResponse,
  SignalFeedResponse,
} from '@/types/chainsight';

const STALE_30M = 1000 * 60 * 30;
const STALE_5M = 1000 * 60 * 5;
const GC_TIME = 1000 * 60 * 60;

export const MARKET_VIEW_KEYS = {
  seeds: ['chainsight', 'seeds'] as const,
  sectorGraph: (sector: string) => ['chainsight', 'sectorGraph', sector] as const,
  neighbors: (symbol: string) => ['chainsight', 'neighbors', symbol] as const,
  signals: (sector?: string) => ['chainsight', 'signals', sector ?? 'all'] as const,
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
