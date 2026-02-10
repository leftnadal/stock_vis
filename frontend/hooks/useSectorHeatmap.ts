import { useQuery } from '@tanstack/react-query';
import { screenerService } from '@/services/screenerService';
import type { SectorHeatmapResponse } from '@/types/screener';

const QUERY_KEYS = {
  sectorHeatmap: (date?: string) => ['sector-heatmap', date] as const,
  allSectorHeatmap: ['sector-heatmap'] as const,
} as const;

export function useSectorHeatmap(date?: string) {
  return useQuery<SectorHeatmapResponse>({
    queryKey: QUERY_KEYS.sectorHeatmap(date),
    queryFn: () => screenerService.getSectorHeatmap(date),
    staleTime: 5 * 60 * 1000, // 5분
    refetchInterval: 5 * 60 * 1000, // 5분마다 자동 갱신
  });
}
