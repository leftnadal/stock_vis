/**
 * Mindmap 카드 화면 TanStack Query hooks (CS-P5-FE-CARD B3+B4)
 *
 * tree = 업종 2단 + 종목 카드 요약(전량 755). card = 카드 상세(연결/그룹/ACQUIRED).
 * staleTime: RelationConfidence 배치 갱신 주기 기준 10분(useChainsight.ts 관례 재사용).
 */

import { useQuery } from '@tanstack/react-query';
import { fetchMindmapTree, fetchMindmapCard } from '@/services/chainsightService';
import type { MindmapTreeResponse, MindmapCardResponse } from '@/types/chainsight';

const STALE_TIME = 1000 * 60 * 10; // 10분
const GC_TIME = 1000 * 60 * 60; // 1시간

export const MINDMAP_KEYS = {
  tree: ['chainsight', 'mindmap', 'tree'] as const,
  card: (symbol: string) => ['chainsight', 'mindmap', 'card', symbol] as const,
};

export function useMindmapTree() {
  return useQuery<MindmapTreeResponse>({
    queryKey: MINDMAP_KEYS.tree,
    queryFn: fetchMindmapTree,
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    networkMode: 'always',
    retry: false,
  });
}

export function useMindmapCard(symbol: string | null) {
  return useQuery<MindmapCardResponse>({
    queryKey: MINDMAP_KEYS.card(symbol ?? ''),
    queryFn: () => fetchMindmapCard(symbol!),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    enabled: !!symbol,
    networkMode: 'always',
    retry: false,
  });
}
