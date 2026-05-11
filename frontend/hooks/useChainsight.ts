/**
 * Chain Sight TanStack Query hooks
 *
 * staleTime: 10분 (Neo4j 동기화 5분마다)
 * gcTime: 1시간
 */

import { useQuery } from '@tanstack/react-query';
import {
  fetchGraph,
  fetchSuggestions,
  fetchTrace,
} from '@/services/chainsightService';
import type {
  GraphResponse,
  SuggestionsResponse,
  TraceResponse,
} from '@/types/chainsight';

const STALE_TIME = 1000 * 60 * 10;    // 10분
const GC_TIME = 1000 * 60 * 60;       // 1시간

export const CHAINSIGHT_KEYS = {
  graph: (symbol: string, depth: number) => ['chainsight', 'graph', symbol, depth] as const,
  suggestions: (symbol: string) => ['chainsight', 'suggestions', symbol] as const,
  trace: (from: string, to: string) => ['chainsight', 'trace', from, to] as const,
};

export function useGraphData(symbol: string, depth: number = 1) {
  return useQuery<GraphResponse>({
    queryKey: CHAINSIGHT_KEYS.graph(symbol, depth),
    queryFn: () => fetchGraph(symbol, depth),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    enabled: !!symbol,
  });
}

export function useSuggestions(symbol: string) {
  return useQuery<SuggestionsResponse>({
    queryKey: CHAINSIGHT_KEYS.suggestions(symbol),
    queryFn: () => fetchSuggestions(symbol),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    enabled: !!symbol,
  });
}

export function useTrace(from: string, to: string) {
  return useQuery<TraceResponse>({
    queryKey: CHAINSIGHT_KEYS.trace(from, to),
    queryFn: () => fetchTrace(from, to),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    enabled: !!from && !!to,
  });
}
