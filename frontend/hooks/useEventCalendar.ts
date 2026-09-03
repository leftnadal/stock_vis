// 이벤트 캘린더 TanStack Query 훅 (EVT-IMPL-4 STEP 3). 키 팩토리는 useMonitor.ts의
// monitorKeys 패턴 동형(all → 파생 하위키).
import { useQuery } from '@tanstack/react-query';

import { eventCalendarService, type EventCalendarQuery } from '@/services/eventCalendarService';
import type { EventFeed, EventStripResponse } from '@/types/eventCalendar';
import type { ChainFeed } from '@/types/chainFeed';

export const eventCalendarKeys = {
  all: ['eventCalendar'] as const,
  feed: (params?: EventCalendarQuery) => [...eventCalendarKeys.all, 'feed', params ?? {}] as const,
  strip: () => [...eventCalendarKeys.all, 'strip'] as const,
  chain: (symbol: string) => [...eventCalendarKeys.all, 'chain', symbol] as const,
};

export function useEventCalendar(params?: EventCalendarQuery) {
  return useQuery<EventFeed>({
    queryKey: eventCalendarKeys.feed(params),
    queryFn: () => eventCalendarService.getCalendar(params),
    staleTime: 1000 * 60 * 5, // 5분
  });
}

// EVT-CHAIN-1: 관계망 이벤트 피드(모니터 상세 scope=stock). symbol이 있을 때만 조회.
export function useChainFeed(symbol: string | null | undefined, enabled = true) {
  return useQuery<ChainFeed>({
    queryKey: eventCalendarKeys.chain((symbol ?? '').toUpperCase()),
    queryFn: () => eventCalendarService.getCalendarChain((symbol ?? '').toUpperCase()),
    staleTime: 1000 * 60 * 5, // 5분
    enabled: enabled && !!symbol,
  });
}

// 홈 이벤트 스트립(S) — NewsStrip/MacroStrip과 동일하게 실패 격리는 컴포넌트가 담당(retry=1).
export function useEventStrip() {
  return useQuery<EventStripResponse>({
    queryKey: eventCalendarKeys.strip(),
    queryFn: () => eventCalendarService.getEventStrip(),
    staleTime: 1000 * 60 * 5, // 5분
    retry: 1,
  });
}
