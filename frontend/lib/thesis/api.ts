import { authAxios } from '@/lib/api/authAxios'
import type {
  Thesis, ThesisIndicator,
  DashboardResponse, ConversationResponse,
  ConversationState, EntrySource,
  AutoRecommendResponse, IndicatorCreatePayload,
  AlertListResponse, CloseResponse,
  IndicatorReadingsResponse,
  SuggestResponse,
} from './types'

const GET   = <T>(url: string) => authAxios.get<T>(url).then(r => r.data)
const POST  = <T>(url: string, data?: unknown) => authAxios.post<T>(url, data).then(r => r.data)
const PATCH = <T>(url: string, data?: unknown) => authAxios.patch<T>(url, data).then(r => r.data)

export const thesisApi = {
  // 가설 CRUD
  list:      ()           => GET<Thesis[]>('/thesis/'),
  get:       (id: string) => GET<Thesis>(`/thesis/${id}/`),
  dashboard: (id: string) => GET<DashboardResponse>(`/thesis/${id}/dashboard/`),

  // 대화형 빌더
  startConversation: (data: { entry_source: EntrySource; source_news_id?: string }) =>
    POST<ConversationResponse>('/thesis/conversation/start/', data),
  suggestTheses: (data: {
    source_news_id: string;
    keyword?: string;
    summary?: string;
    sentiment?: string;
  }) => POST<SuggestResponse>('/thesis/conversation/suggest/', data),
  sendMessage: (data: {
    conversation_state: ConversationState;
    user_input: string | string[];
  }) => POST<ConversationResponse>('/thesis/conversation/respond/', data),

  // 지표
  listIndicators: (thesisId: string) =>
    GET<ThesisIndicator[]>(`/thesis/${thesisId}/indicators/`),
  autoRecommend: (thesisId: string, premiseId?: string) =>
    POST<AutoRecommendResponse>(
      `/thesis/${thesisId}/indicators/auto/`,
      premiseId ? { premise_id: premiseId } : {},
    ),
  addIndicator: (thesisId: string, data: IndicatorCreatePayload) =>
    POST<ThesisIndicator>(`/thesis/${thesisId}/indicators/`, data),
  removeIndicator: (thesisId: string, indicatorId: string) =>
    authAxios.delete(`/thesis/${thesisId}/indicators/${indicatorId}/`).then(() => undefined),
  toggleIndicator: (thesisId: string, indicatorId: string, isActive: boolean) =>
    PATCH<ThesisIndicator>(
      `/thesis/${thesisId}/indicators/${indicatorId}/`,
      { is_active: isActive },
    ),

  // 차트 readings
  indicatorReadings: (thesisId: string, indicatorId: string, days: number = 14) =>
    GET<IndicatorReadingsResponse>(
      `/thesis/${thesisId}/indicators/${indicatorId}/readings/?days=${days}`
    ),

  // 알림
  listAlerts:    () =>
    GET<AlertListResponse>('/thesis/alerts/'),
  markAlertRead: (alertId: string) =>
    PATCH<void>(`/thesis/alerts/${alertId}/read/`, {}),

  // 마감
  close: (id: string, data: { outcome: string; outcome_note?: string }) =>
    POST<CloseResponse>(`/thesis/${id}/close/`, data),
}
