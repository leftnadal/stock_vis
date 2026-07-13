/** Market Pulse v2 — TanStack Query hooks (PR-K/L). */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  fetchCardDetail,
  fetchOverview,
  fetchRegimeAnalog,
  fetchRegimeZScore,
  refreshNews,
  type CardDetailEnvelope,
  type OverviewResponse,
  type RegimeAnalogPayload,
  type RegimeZScorePayload,
} from '@/lib/api/marketPulseV2'

const OVERVIEW_QUERY_KEY = ['marketpulse-v2', 'overview'] as const
const CARD_DETAIL_KEY = (cardId: string) =>
  ['marketpulse-v2', 'card', cardId, 'detail'] as const
const REGIME_ZSCORE_KEY = ['marketpulse-v2', 'regime', 'zscore'] as const
const REGIME_ANALOG_KEY = ['marketpulse-v2', 'regime', 'analog'] as const

export function useOverview() {
  return useQuery<OverviewResponse>({
    queryKey: OVERVIEW_QUERY_KEY,
    queryFn: fetchOverview,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}

export function useCardDetail<T = unknown>(
  cardId: 'regime' | 'breadth' | 'sector' | 'concentration' | 'brief',
  enabled: boolean = true,
) {
  return useQuery<CardDetailEnvelope<T>>({
    queryKey: CARD_DETAIL_KEY(cardId),
    queryFn: () => fetchCardDetail<T>(cardId),
    enabled,
    staleTime: cardId === 'brief' ? 30 * 60 * 1000 : 5 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  })
}

// MP2-TREND S4: z-이상도 lazy fetch — z 탭 열릴 때만(enabled). baseline 24h(BE 캐시), FE 30분.
export function useRegimeZScore(enabled: boolean = false) {
  return useQuery<CardDetailEnvelope<RegimeZScorePayload>>({
    queryKey: REGIME_ZSCORE_KEY,
    queryFn: fetchRegimeZScore,
    enabled,
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  })
}

// MP2-ANALOG Slice B: 유사 국면 카드 fetch(enabled 시). BE 1h 캐시, FE 30분.
export function useRegimeAnalog(enabled: boolean = true) {
  return useQuery<CardDetailEnvelope<RegimeAnalogPayload>>({
    queryKey: REGIME_ANALOG_KEY,
    queryFn: fetchRegimeAnalog,
    enabled,
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  })
}

export function useRefreshNews() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: refreshNews,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: OVERVIEW_QUERY_KEY })
    },
  })
}
