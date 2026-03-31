/**
 * 1차 검증 API client
 */

import type {
  ValidationSummary,
  ValidationMetricsResponse,
  LeaderComparison,
  PresetListResponse,
} from '@/types/validation';

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

export async function fetchValidationSummary(symbol: string): Promise<ValidationSummary> {
  return fetchJson<ValidationSummary>(`${API_URL}/validation/${symbol.toUpperCase()}/summary/`);
}

export async function fetchValidationMetrics(
  symbol: string,
  category: string = 'all'
): Promise<ValidationMetricsResponse> {
  return fetchJson<ValidationMetricsResponse>(
    `${API_URL}/validation/${symbol.toUpperCase()}/metrics/?category=${category}`
  );
}

export async function fetchLeaderComparison(symbol: string): Promise<LeaderComparison> {
  return fetchJson<LeaderComparison>(`${API_URL}/validation/${symbol.toUpperCase()}/leader-comparison/`);
}

export async function fetchPresets(symbol: string): Promise<PresetListResponse> {
  return fetchJson<PresetListResponse>(`${API_URL}/validation/${symbol.toUpperCase()}/presets/`);
}

export async function selectPreset(symbol: string, presetKey: string): Promise<void> {
  await fetch(`${API_URL}/validation/${symbol.toUpperCase()}/peer-preference/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ mode: 'preset', preset_key: presetKey }),
  });
}
