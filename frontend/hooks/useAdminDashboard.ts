import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminService } from '@/services/adminService';
import type { TaskLogParams, NewsCategoryCreateRequest, NewsCategoryUpdateRequest } from '@/types/admin';

const ADMIN_KEYS = {
  overview: ['admin', 'overview'] as const,
  stocks: ['admin', 'stocks'] as const,
  screener: ['admin', 'screener'] as const,
  marketPulse: ['admin', 'market-pulse'] as const,
  news: ['admin', 'news'] as const,
  system: ['admin', 'system'] as const,
  taskLogs: (params?: TaskLogParams) => ['admin', 'task-logs', params] as const,
  health: ['admin', 'health'] as const,
  providers: ['admin', 'providers'] as const,
  newsCategories: ['admin', 'news-categories'] as const,
  sectorOptions: ['admin', 'sector-options'] as const,
};

export function useAdminOverview() {
  return useQuery({
    queryKey: ADMIN_KEYS.overview,
    queryFn: () => adminService.getOverview(),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useAdminStocks() {
  return useQuery({
    queryKey: ADMIN_KEYS.stocks,
    queryFn: () => adminService.getStocksStatus(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useAdminScreener() {
  return useQuery({
    queryKey: ADMIN_KEYS.screener,
    queryFn: () => adminService.getScreenerStatus(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useAdminMarketPulse() {
  return useQuery({
    queryKey: ADMIN_KEYS.marketPulse,
    queryFn: () => adminService.getMarketPulseStatus(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useAdminNews() {
  return useQuery({
    queryKey: ADMIN_KEYS.news,
    queryFn: () => adminService.getNewsStatus(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useAdminSystem() {
  return useQuery({
    queryKey: ADMIN_KEYS.system,
    queryFn: () => adminService.getSystemStatus(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useAdminTaskLogs(params?: TaskLogParams) {
  return useQuery({
    queryKey: ADMIN_KEYS.taskLogs(params),
    queryFn: () => adminService.getTaskLogs(params),
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  });
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ADMIN_KEYS.health,
    queryFn: () => adminService.getHealthCheck(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useProviderStatus() {
  return useQuery({
    queryKey: ADMIN_KEYS.providers,
    queryFn: () => adminService.getProviderStatus(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useNewsCategories() {
  return useQuery({
    queryKey: ADMIN_KEYS.newsCategories,
    queryFn: () => adminService.getNewsCategories(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useSectorOptions() {
  return useQuery({
    queryKey: ADMIN_KEYS.sectorOptions,
    queryFn: () => adminService.getSectorOptions(),
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useNewsCategoryMutations() {
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ADMIN_KEYS.newsCategories });
    queryClient.invalidateQueries({ queryKey: ADMIN_KEYS.news });
  };

  const create = useMutation({
    mutationFn: (data: NewsCategoryCreateRequest) => adminService.createNewsCategory(data),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: number; data: NewsCategoryUpdateRequest }) =>
      adminService.updateNewsCategory(id, data),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (id: number) => adminService.deleteNewsCategory(id),
    onSuccess: invalidate,
  });

  return { create, update, remove };
}
