// 이벤트 캘린더 API 클라이언트 (EVT-IMPL-4 STEP 3).
// calendar = authAxios(base=/api/v1 포함, common-bug #19) → /monitor/calendar/ 상대경로.
// strip = /api/dashboard/event-strip/ — v1 밖의 dashboard BFF라 stripService.ts 선례 그대로
// ORIGIN 절대경로로 호출한다(authAxios 유지 = JWT 인터셉터는 그대로, base만 우회).
import { API_BASE_URL } from '@/lib/api/config';
import { authAxios } from '@/lib/api/authAxios';
import type { EventFeed, EventScope, EventStripResponse } from '@/types/eventCalendar';

const ORIGIN = API_BASE_URL.replace(/\/api\/v1\/?$/, '');

export interface EventCalendarQuery {
  from?: string;
  to?: string;
  scope?: EventScope;
  kinds?: string; // csv
  include_stale?: boolean;
  macro_min_importance?: string;
}

export const eventCalendarService = {
  async getCalendar(params?: EventCalendarQuery): Promise<EventFeed> {
    const { data } = await authAxios.get<EventFeed>('/monitor/calendar/', { params });
    return data;
  },

  async getEventStrip(): Promise<EventStripResponse> {
    const { data } = await authAxios.get<EventStripResponse>(
      `${ORIGIN}/api/dashboard/event-strip/`,
    );
    return data;
  },
};
