import { useQuery } from '@tanstack/react-query';
import { newsPipelineService } from '@/services/newsPipelineService';

const PIPELINE_KEYS = {
  health: ['news-pipeline', 'health'] as const,
  collectionLogs: (days: number) => ['news-pipeline', 'collection-logs', days] as const,
  mlTrend: (weeks: number) => ['news-pipeline', 'ml-trend', weeks] as const,
  llmUsage: (days: number) => ['news-pipeline', 'llm-usage', days] as const,
};

export function usePipelineHealth(enabled = true) {
  return useQuery({
    queryKey: PIPELINE_KEYS.health,
    queryFn: () => newsPipelineService.getPipelineHealth(),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    enabled,
  });
}

export function useCollectionLogs(days = 7, enabled = true) {
  return useQuery({
    queryKey: PIPELINE_KEYS.collectionLogs(days),
    queryFn: () => newsPipelineService.getCollectionLogs(days),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    enabled,
  });
}

export function useMLTrend(weeks = 12, enabled = true) {
  return useQuery({
    queryKey: PIPELINE_KEYS.mlTrend(weeks),
    queryFn: () => newsPipelineService.getMLTrend(weeks),
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
    enabled,
  });
}

export function useLLMUsage(days = 30, enabled = true) {
  return useQuery({
    queryKey: PIPELINE_KEYS.llmUsage(days),
    queryFn: () => newsPipelineService.getLLMUsage(days),
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
    enabled,
  });
}
