import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as api from '@/services/pathWatchlistService';
import type { WatchPathInput } from '@/types/pathWatchlist';

export const PATH_WATCHLIST_KEYS = {
  all: ['pathWatchlist'] as const,
  list: (status?: string) => ['pathWatchlist', 'list', status ?? 'all'] as const,
  detail: (id: string) => ['pathWatchlist', 'detail', id] as const,
};

export function useWatchlist(status?: string) {
  return useQuery({
    queryKey: PATH_WATCHLIST_KEYS.list(status),
    queryFn: () => api.fetchWatchlist(status),
    staleTime: 30_000,
  });
}

export function usePathDetail(id: string | null) {
  return useQuery({
    queryKey: PATH_WATCHLIST_KEYS.detail(id ?? ''),
    queryFn: () => api.fetchPathDetail(id!),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useWatchPath() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: WatchPathInput) => api.watchPath(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: PATH_WATCHLIST_KEYS.all }); },
    onError: () => { toast.error('경로 저장에 실패했어요'); },
  });
}

export function useRecheckPath() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.recheckPath(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: PATH_WATCHLIST_KEYS.detail(id) });
      qc.invalidateQueries({ queryKey: PATH_WATCHLIST_KEYS.all });
    },
    onError: () => { toast.error('Recheck에 실패했어요'); },
  });
}

export function useExpandPath() {
  return useMutation({
    mutationFn: ({ id, targetTicker, limit }: { id: string; targetTicker?: string; limit?: number }) =>
      api.expandPath(id, targetTicker, limit),
    onError: () => { toast.error('Expand에 실패했어요'); },
  });
}

export function useAlternatives() {
  return useMutation({
    mutationFn: ({ id, targetTicker, limit }: { id: string; targetTicker: string; limit?: number }) =>
      api.findAlternatives(id, targetTicker, limit),
    onError: () => { toast.error('Alternatives 탐색에 실패했어요'); },
  });
}

export function useArchivePath() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.archivePath(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: PATH_WATCHLIST_KEYS.detail(id) });
      qc.invalidateQueries({ queryKey: PATH_WATCHLIST_KEYS.all });
      toast.success('경로가 보관되었어요');
    },
    onError: () => { toast.error('Archive에 실패했어요'); },
  });
}

export function useResolvePath() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.resolvePath(id),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: PATH_WATCHLIST_KEYS.detail(id) });
      qc.invalidateQueries({ queryKey: PATH_WATCHLIST_KEYS.all });
      toast.success('전략이 종료되었어요');
    },
    onError: () => { toast.error('Resolve에 실패했어요'); },
  });
}

export function useDeletePath() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deletePath(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PATH_WATCHLIST_KEYS.all });
      toast.success('경로가 삭제되었어요');
    },
    onError: () => { toast.error('삭제에 실패했어요'); },
  });
}
