/** Market Pulse v2 i18n hook (24h cache). */
import { useQuery } from '@tanstack/react-query'

import { fetchI18n, type I18nResponse } from '@/lib/api/marketPulseV2'

const I18N_QUERY_KEY = ['marketpulse-v2', 'i18n', 'ko'] as const

const FALLBACK_LABELS: Record<string, string> = {
  'card.regime': 'Market Regime',
  'card.breadth': 'Market Breadth',
  'card.sector': 'Sector Flow',
  'card.concentration': 'Concentration',
  'card.brief': 'Briefing',
  'mode.ANOMALY': 'Anomaly',
  'mode.HYBRID': 'Hybrid',
  'mode.CALM': 'Calm',
}

export function useMarketPulseI18n() {
  return useQuery<I18nResponse>({
    queryKey: I18N_QUERY_KEY,
    queryFn: () => fetchI18n('ko'),
    staleTime: 24 * 60 * 60 * 1000,
    gcTime: 25 * 60 * 60 * 1000,
    retry: 1,
  })
}

export function translate(
  key: string,
  labels: Record<string, string> | undefined,
  defaultText?: string,
): string {
  if (labels && labels[key]) return labels[key]
  if (FALLBACK_LABELS[key]) return FALLBACK_LABELS[key]
  return defaultText ?? key
}
