/**
 * RC-C-1 backbone TanStack Query 훅 (useEgo 선례 동형).
 */

import { useQuery } from '@tanstack/react-query';
import { fetchBackbone } from '@/services/backboneService';
import type { BackboneResponse } from '@/types/backbone';

const STALE_15M = 1000 * 60 * 15; // BE 캐시 15분과 동형
const GC_TIME = 1000 * 60 * 60;

export const BACKBONE_KEYS = {
  root: (limit: number) => ['chainsight', 'backbone', limit] as const,
};

export function useBackbone(limit = 20) {
  return useQuery<BackboneResponse>({
    queryKey: BACKBONE_KEYS.root(limit),
    queryFn: () => fetchBackbone(limit),
    staleTime: STALE_15M,
    gcTime: GC_TIME,
    // ⑳-E 선례: pause 없이 실패를 error 로 확정 → 로드 에러 상태 신뢰성.
    networkMode: 'always',
    retry: false,
  });
}
