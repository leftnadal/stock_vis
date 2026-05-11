import { authAxios } from '@/lib/api/authAxios';
import type {
  SavedPathListItem, SavedPathDetail, WatchPathInput,
  RecheckResponse, ExpandResponse, AlternativesResponse,
} from '@/types/pathWatchlist';

export async function watchPath(data: WatchPathInput): Promise<SavedPathDetail> {
  const { data: result } = await authAxios.post<SavedPathDetail>('/chainsight/watchlist/', data);
  return result;
}

export async function fetchWatchlist(status?: string): Promise<SavedPathListItem[]> {
  const { data } = await authAxios.get<SavedPathListItem[]>('/chainsight/watchlist/', {
    params: status ? { status } : undefined,
  });
  return data;
}

export async function fetchPathDetail(id: string): Promise<SavedPathDetail> {
  const { data } = await authAxios.get<SavedPathDetail>(`/chainsight/watchlist/${id}/`);
  return data;
}

export async function deletePath(id: string): Promise<void> {
  await authAxios.delete(`/chainsight/watchlist/${id}/`);
}

export async function archivePath(id: string): Promise<SavedPathDetail> {
  const { data } = await authAxios.post<SavedPathDetail>(`/chainsight/watchlist/${id}/archive/`);
  return data;
}

export async function resolvePath(id: string): Promise<SavedPathDetail> {
  const { data } = await authAxios.post<SavedPathDetail>(`/chainsight/watchlist/${id}/resolve/`);
  return data;
}

export async function recheckPath(id: string): Promise<RecheckResponse> {
  const { data } = await authAxios.post<RecheckResponse>(`/chainsight/watchlist/${id}/recheck/`);
  return data;
}

export async function expandPath(id: string, targetTicker?: string, limit?: number): Promise<ExpandResponse> {
  const { data } = await authAxios.post<ExpandResponse>(`/chainsight/watchlist/${id}/expand/`, {
    target_ticker: targetTicker, limit,
  });
  return data;
}

export async function findAlternatives(id: string, targetTicker: string, limit?: number): Promise<AlternativesResponse> {
  const { data } = await authAxios.post<AlternativesResponse>(`/chainsight/watchlist/${id}/alternatives/`, {
    target_ticker: targetTicker, limit,
  });
  return data;
}
