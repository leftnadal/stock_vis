import { authAxios } from '@/lib/api/authAxios'
import type {
  Thesis, ThesisAlert, ThesisIndicator,
  DashboardResponse, ConversationResponse,
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
  startConversation: (data: { entry_source: string; news_id?: string }) =>
    POST<ConversationResponse>('/thesis/conversation/start/', data),
  sendMessage: (data: { session_id: string; message: string }) =>
    POST<ConversationResponse>('/thesis/conversation/respond/', data),

  // 지표
  listIndicators: (thesisId: string) =>
    GET<ThesisIndicator[]>(`/thesis/${thesisId}/indicators/`),
  autoRecommend:  (thesisId: string) =>
    POST<ThesisIndicator[]>(`/thesis/${thesisId}/indicators/auto-recommend/`, {}),

  // 알림
  listAlerts:    (thesisId?: string) =>
    GET<ThesisAlert[]>(thesisId ? `/thesis/${thesisId}/alerts/` : '/thesis/alerts/'),
  markAlertRead: (alertId: string) =>
    PATCH<void>(`/thesis/alerts/${alertId}/read/`, {}),

  // 마감
  close: (id: string, data: { outcome: string; outcome_note?: string }) =>
    PATCH<Thesis>(`/thesis/${id}/close/`, data),
}
