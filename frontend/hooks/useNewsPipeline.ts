import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { newsPipelineService } from '@/services/newsPipelineService';

const PIPELINE_KEYS = {
  base: ['news-pipeline'] as const,
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
    refetchInterval: 5 * 60_000,
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

export function useTaskTimeline(hours = 24, enabled = true) {
  return useQuery({
    queryKey: [...PIPELINE_KEYS.base, 'timeline', hours],
    queryFn: () => newsPipelineService.getTaskTimeline(hours),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
    refetchOnWindowFocus: false,
    enabled,
  });
}

export function useNeo4jStatus(enabled = true) {
  return useQuery({
    queryKey: [...PIPELINE_KEYS.base, 'neo4j'],
    queryFn: () => newsPipelineService.getNeo4jStatus(),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
    refetchOnWindowFocus: false,
    enabled,
  });
}

export function useMLRollbackPreview(enabled = false) {
  return useQuery({
    queryKey: [...PIPELINE_KEYS.base, 'rollback-preview'],
    queryFn: () => newsPipelineService.getMLRollbackPreview(),
    staleTime: 0,
    refetchOnWindowFocus: false,
    enabled,
  });
}

export function useMLRollback() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => newsPipelineService.executeMLRollback(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PIPELINE_KEYS.health });
    },
  });
}

export function useAlerts(
  params?: { resolved?: boolean; severity?: string; limit?: number },
  enabled = true
) {
  return useQuery({
    queryKey: [...PIPELINE_KEYS.base, 'alerts', params],
    queryFn: () => newsPipelineService.getAlerts(params),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    enabled,
  });
}

export function useResolveAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      alertId,
      acknowledgedBy,
    }: {
      alertId: number;
      acknowledgedBy?: string;
    }) => newsPipelineService.resolveAlert(alertId, acknowledgedBy),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [...PIPELINE_KEYS.base, 'alerts'],
      });
    },
  });
}
