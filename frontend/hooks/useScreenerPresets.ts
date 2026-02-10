import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { screenerService } from '@/services/screenerService';
import type {
  ScreenerPresetsResponse,
  CreatePresetPayload,
  ScreenerPreset,
} from '@/types/screener';

const QUERY_KEYS = {
  presets: (category?: string) => ['screener-presets', category] as const,
  allPresets: ['screener-presets'] as const,
} as const;

export function useScreenerPresets(category?: string) {
  return useQuery<ScreenerPresetsResponse>({
    queryKey: QUERY_KEYS.presets(category),
    queryFn: () => screenerService.getPresets(category),
    staleTime: 10 * 60 * 1000, // 10분
  });
}

export function useCreatePreset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreatePresetPayload) => screenerService.createPreset(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.allPresets });
    },
  });
}

export function useDeletePreset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (presetId: number) => screenerService.deletePreset(presetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.allPresets });
    },
  });
}
