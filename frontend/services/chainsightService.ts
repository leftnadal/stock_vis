/**
 * Chain Sight API 클라이언트
 *
 * authAxios 사용: JWT 인터셉터 단일 소스 (lib/api/authAxios.ts)
 */

import { authAxios } from '@/lib/api/authAxios';
import type {
  GraphResponse,
  SuggestionsResponse,
  TraceResponse,
  SeedResponse,
  SectorGraphResponse,
  NeighborResponse,
  SignalFeedResponse,
  EventBoardItem,
  EventRankingItem,
} from '@/types/chainsight';

export async function fetchGraph(symbol: string, depth: number = 1): Promise<GraphResponse> {
  const { data } = await authAxios.get<GraphResponse>(
    `/chainsight/${symbol.toUpperCase()}/graph/`,
    { params: { depth } },
  );
  return data;
}

export async function fetchSuggestions(symbol: string): Promise<SuggestionsResponse> {
  const { data } = await authAxios.get<SuggestionsResponse>(
    `/chainsight/${symbol.toUpperCase()}/suggestions/`,
  );
  return data;
}

export async function fetchTrace(from: string, to: string): Promise<TraceResponse> {
  const { data } = await authAxios.get<TraceResponse>('/chainsight/trace/', {
    params: { from: from.toUpperCase(), to: to.toUpperCase() },
  });
  return data;
}

// ── Market View API ──

export async function fetchSeeds(): Promise<SeedResponse> {
  const { data } = await authAxios.get<SeedResponse>('/chainsight/seeds/');
  return data;
}

export async function fetchSectorGraph(sector: string, limit = 12): Promise<SectorGraphResponse> {
  const { data } = await authAxios.get<SectorGraphResponse>(
    `/chainsight/sector/${encodeURIComponent(sector)}/graph/`,
    { params: { limit } },
  );
  return data;
}

export async function fetchNeighbors(
  symbol: string,
  limit = 8,
  relTypes = 'all',
  minTruthScore = 35,
): Promise<NeighborResponse> {
  const { data } = await authAxios.get<NeighborResponse>(
    `/chainsight/${symbol.toUpperCase()}/neighbors/`,
    { params: { limit, rel_types: relTypes, min_truth_score: minTruthScore } },
  );
  return data;
}

export async function fetchSignals(page = 1, pageSize = 5, sector?: string): Promise<SignalFeedResponse> {
  const { data } = await authAxios.get<SignalFeedResponse>('/chainsight/signals/', {
    params: { page, page_size: pageSize, ...(sector && { sector }) },
  });
  return data;
}

// ── Event Board API (CS-RD3) ──

export async function fetchEvents(): Promise<EventBoardItem[]> {
  const { data } = await authAxios.get<EventBoardItem[]>('/chainsight/events/');
  return data;
}

/**
 * 테마 종목 랭킹 조회. window = M2 주도주 지표 윈도우(20=최신 모멘텀 / 120=중기).
 * 기존 호출 호환을 위해 window 옵셔널 + 기본 20. (셀렉터 UI는 S3에서 연결)
 */
export async function fetchEventStocks(
  theme: string,
  window: 20 | 120 = 20,
): Promise<EventRankingItem[]> {
  const { data } = await authAxios.get<EventRankingItem[]>(
    `/chainsight/events/${encodeURIComponent(theme)}/stocks/`,
    { params: { window } },
  );
  return data;
}
