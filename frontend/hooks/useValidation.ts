/**
 * 1차 검증 TanStack Query hooks
 *
 * staleTime: 1시간 (데이터가 주 1회 갱신이므로 충분)
 * gcTime: 24시간
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchValidationSummary,
  fetchValidationMetrics,
  fetchLeaderComparison,
  fetchPresets,
  selectPreset,
} from '@/services/validation';
import type {
  ValidationSummary,
  ValidationMetricsResponse,
  LeaderComparison,
  PresetListResponse,
} from '@/types/validation';

const STALE_TIME = 1000 * 60 * 60;      // 1시간
const GC_TIME = 1000 * 60 * 60 * 24;    // 24시간

export const VALIDATION_QUERY_KEYS = {
  summary: (symbol: string) => ['validation', 'summary', symbol] as const,
  metrics: (symbol: string, category: string) => ['validation', 'metrics', symbol, category] as const,
  leader: (symbol: string) => ['validation', 'leader', symbol] as const,
  presets: (symbol: string) => ['validation', 'presets', symbol] as const,
};

export function useValidationSummary(symbol: string) {
  return useQuery<ValidationSummary>({
    queryKey: VALIDATION_QUERY_KEYS.summary(symbol),
    queryFn: () => fetchValidationSummary(symbol),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    enabled: !!symbol,
  });
}

export function useValidationMetrics(symbol: string, category: string = 'all') {
  return useQuery<ValidationMetricsResponse>({
    queryKey: VALIDATION_QUERY_KEYS.metrics(symbol, category),
    queryFn: () => fetchValidationMetrics(symbol, category),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    enabled: !!symbol,
  });
}

export function useLeaderComparison(symbol: string) {
  return useQuery<LeaderComparison>({
    queryKey: VALIDATION_QUERY_KEYS.leader(symbol),
    queryFn: () => fetchLeaderComparison(symbol),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    enabled: !!symbol,
  });
}

export function usePresets(symbol: string) {
  return useQuery<PresetListResponse>({
    queryKey: VALIDATION_QUERY_KEYS.presets(symbol),
    queryFn: () => fetchPresets(symbol),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    enabled: !!symbol,
  });
}

export function useSelectPreset(symbol: string) {
  const queryClient = useQueryClient();
  return async (presetKey: string) => {
    await selectPreset(symbol, presetKey);
    // 프리셋 목록 + summary + metrics 캐시 무효화
    queryClient.invalidateQueries({ queryKey: VALIDATION_QUERY_KEYS.presets(symbol) });
    queryClient.invalidateQueries({ queryKey: VALIDATION_QUERY_KEYS.summary(symbol) });
    queryClient.invalidateQueries({ queryKey: ['validation', 'metrics', symbol] });
    queryClient.invalidateQueries({ queryKey: VALIDATION_QUERY_KEYS.leader(symbol) });
  };
}
