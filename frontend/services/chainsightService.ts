/**
 * Chain Sight API 클라이언트
 */

import type {
  GraphResponse,
  SuggestionsResponse,
  TraceResponse,
} from '@/types/chainsight';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchGraph(symbol: string, depth: number = 1): Promise<GraphResponse> {
  return fetchJson<GraphResponse>(
    `${API_URL}/chainsight/${symbol.toUpperCase()}/graph/?depth=${depth}`
  );
}

export async function fetchSuggestions(symbol: string): Promise<SuggestionsResponse> {
  return fetchJson<SuggestionsResponse>(
    `${API_URL}/chainsight/${symbol.toUpperCase()}/suggestions/`
  );
}

export async function fetchTrace(from: string, to: string): Promise<TraceResponse> {
  return fetchJson<TraceResponse>(
    `${API_URL}/chainsight/trace/?from=${from.toUpperCase()}&to=${to.toUpperCase()}`
  );
}
