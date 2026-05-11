/** Market Pulse v2 — TanStack Query hooks (PR-K/L). */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  fetchCardDetail,
  fetchOverview,
  refreshNews,
  type CardDetailEnvelope,
  type OverviewResponse,
} from '@/lib/api/marketPulseV2'

const OVERVIEW_QUERY_KEY = ['marketpulse-v2', 'overview'] as const
const CARD_DETAIL_KEY = (cardId: string) =>
  ['marketpulse-v2', 'card', cardId, 'detail'] as const

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
  cardId: 'regime' | 'breadth' | 'sector' | 'flow' | 'brief',
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

export function useRefreshNews() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: refreshNews,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: OVERVIEW_QUERY_KEY })
    },
  })
}
