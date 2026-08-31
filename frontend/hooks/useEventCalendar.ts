// 이벤트 캘린더 TanStack Query 훅 (EVT-IMPL-4 STEP 3). 키 팩토리는 useMonitor.ts의
// monitorKeys 패턴 동형(all → 파생 하위키).
import { useQuery } from '@tanstack/react-query';

import { eventCalendarService, type EventCalendarQuery } from '@/services/eventCalendarService';
import type { EventFeed, EventStripResponse } from '@/types/eventCalendar';

export const eventCalendarKeys = {
  all: ['eventCalendar'] as const,
  feed: (params?: EventCalendarQuery) => [...eventCalendarKeys.all, 'feed', params ?? {}] as const,
  strip: () => [...eventCalendarKeys.all, 'strip'] as const,
};

export function useEventCalendar(params?: EventCalendarQuery) {
  return useQuery<EventFeed>({
    queryKey: eventCalendarKeys.feed(params),
    queryFn: () => eventCalendarService.getCalendar(params),
    staleTime: 1000 * 60 * 5, // 5분
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
