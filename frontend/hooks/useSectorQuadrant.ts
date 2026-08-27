// DSS-QUADRANT 데이터 훅 (QUAD-IMPL-1 Slice 2)
import { useQuery } from '@tanstack/react-query';
import { authAxios } from '@/lib/api/authAxios';
import type { QuadrantResponse } from '@/types/quadrant';

export const SECTOR_QUADRANT_KEY = ['sector-quadrant'] as const;

export function useSectorQuadrant() {
  return useQuery<QuadrantResponse>({
    queryKey: SECTOR_QUADRANT_KEY,
    queryFn: async () => {
      const { data } = await authAxios.get<QuadrantResponse>(
        '/chainsight/theme-heat/quadrant/',
      );
      return data;
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}
