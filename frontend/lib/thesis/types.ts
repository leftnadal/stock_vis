// ═══ 진입점 소스 (백엔드 ALLOWED_ENTRY_SOURCES 화이트리스트) ═══

export const ENTRY_SOURCES = ['news', 'free_input', 'popular', 'template', 'chainsight'] as const
export type EntrySource = (typeof ENTRY_SOURCES)[number]

// ═══ 열거형 ═══

export type Direction = 'bullish' | 'bearish' | 'neutral'

export type ThesisStatus = 'setting_up' | 'active' | 'closed' | 'paused'

export type ThesisState =
  | 'warming_up' | 'active' | 'strengthening' | 'weakening'
  | 'critical' | 'needs_review' | 'expired'
  | 'closed_correct' | 'closed_incorrect' | 'closed_neutral'

export type IndicatorType =
  | 'market_data' | 'macro' | 'sentiment' | 'technical' | 'custom'

export type SupportDirection = 'positive' | 'negative'

// ═══ 엔티티 ═══

export interface Thesis {
  id: string
  user: number
  title: string
  direction: Direction
  target: string
  thesis_type: string            // 'event' | 'trend' | 'comparison' | 'divergence' | 'custom'
  status: ThesisStatus
  current_state: ThesisState
  current_score: number | null   // null = warming_up
  overall_label: string
  ai_summary: string | null
  expected_timeframe: string | null
  entry_source: string            // 'news' | 'free_input' | 'popular' | 'template' | 'chainsight'
  created_at: string             // ISO 8601
  closed_at: string | null
  outcome: string | null         // 'correct' | 'incorrect' | 'neutral'
  outcome_note: string
}

export interface ThesisPremise {
  id: string
  content: string
  extraction_level: 'explicit' | 'implicit' | 'ai_suggested'
  is_active: boolean
  current_score: number          // -1.0 ~ 1.0
  current_label: string
  order: number
}

export interface ThesisIndicator {
  id: string
  name: string
  indicator_type: IndicatorType
  support_direction: SupportDirection
  current_arrow_degree: number   // 0 ~ 180 (프론트 alias, 백엔드: current_degree)
  current_label: string
  current_color: string          // hex 색상 코드
  is_active: boolean
  premise: string | null         // premise id
  // PR-4 추가 필드
  data_source: string            // 'fmp' | 'fred' | 'news_sentiment' | 'manual' | 'custom'
  data_params: Record<string, string | number>
  weight: number
  is_paused: boolean
  current_score: number | null
  created_at: string             // ISO 8601
}

export interface ThesisAlert {
  id: string
  thesis: string                 // thesis id
  indicator: string | null       // ThesisIndicator id, 지표 무관 알림이면 null
  alert_type: string             // 'indicator_change' | 'threshold_cross' | 'news_event' | 'target_date' | 'daily_summary'
  severity: string               // 'info' | 'warning' | 'critical'
  title: string
  message: string
  is_read: boolean
  is_pushed: boolean
  created_at: string
}

export interface AlertListResponse {
  alerts: ThesisAlert[]
  unread_count: number
}

export interface CloseResponse {
  status: string
  thesis_id: string
}

// ═══ API 응답 ═══

// 대시보드 전용 thesis (백엔드가 축약해서 반환)
export interface DashboardThesis {
  id: string
  title: string
  direction: Direction
  status: ThesisStatus
  days_active: number
  overall_score: number          // -1.0 ~ 1.0
  overall_label: string          // '가설이 빛나고 있어요' 등
  overall_phase: string          // 'full_moon' | 'waxing' | 'half_moon' | 'waning' | 'new_moon'
  recent_change: string          // 최신 변화 텍스트 (1줄)
  overall_delta?: number | null  // 전일 대비 전체 점수 변화 (백엔드 추가 시 활용)
}

// 대시보드 전용 indicator (ThesisIndicator와 필드명 다름)
export interface DashboardIndicator {
  id: string
  name: string
  arrow_degree: number           // 0~180 (소수점 1자리)
  score: number                  // -1.0 ~ 1.0
  color: string                  // hex
  label: string                  // '지지하는 편' 등 (특수 라벨 포함)
  previous_degree: number | null // 이전 각도 (trend 계산용)
  trend: 'stable' | 'strengthening' | 'weakening'
  premise_name: string           // premise.content[:50]
  is_extreme_vol: boolean        // |z_raw| >= 5.0
}

// 히트맵 셀
export interface HeatmapCell {
  name: string                   // 지표명 (최대 10자)
  color: string                  // hex
  degree: number                 // 0~180
}

// 히트맵 데이터
export interface HeatmapData {
  rows: number
  cols: number
  cells: HeatmapCell[]
}

// 교정된 DashboardResponse (백엔드 실제 응답)
export interface DashboardResponse {
  thesis: DashboardThesis
  indicators: DashboardIndicator[]
  heatmap: HeatmapData
}

export interface ConversationButton {
  id: string
  label: string
  type?: 'text_input'
  long_press_hint?: boolean
}

// ═══ 대화 상태 (백엔드 conversation_state echo) ═══

export interface ConversationState {
  conv_id: string
  entry_source: EntrySource
  step: number
  collected: Record<string, unknown>
  source_news_id?: string
}

// ═══ 미리보기 (step 5/6에서 출현) ═══

export interface PreviewPremise {
  content: string
  category: string
}

export interface PreviewIndicator {
  name: string
  indicator_type: string
}

export interface ThesisPreview {
  title: string
  direction: Direction
  premises: PreviewPremise[]
  indicators: PreviewIndicator[]
}

export interface ConversationResponse {
  message: string
  buttons: ConversationButton[]
  selection_mode: 'single' | 'multi'
  long_press_explanations?: Record<string, string>
  conversation_state: ConversationState
  step: number
  total_steps: number
  input_type?: 'text'
  preview?: ThesisPreview
  thesis_id?: string
  done?: boolean
  counter_thesis_id?: string
  thesis?: Thesis
}

// ═══ PR-4: AI 추천 결과 (아직 DB에 저장되지 않은 상태) ═══

export interface RecommendedIndicator {
  name: string
  data_source: string
  data_params: Record<string, string | number>
  indicator_type: string
  support_direction: SupportDirection
  reason: string
}

// ═══ PR-4: 지표 생성 요청 본문 ═══

export interface IndicatorCreatePayload {
  name: string
  indicator_type: string
  data_source: string
  data_params: Record<string, string | number>
  support_direction: SupportDirection
  weight?: number
  premise?: string | null
  is_ai_recommended?: boolean
}

// ═══ PR-4: auto-recommend 응답 ═══

export interface AutoRecommendResponse {
  indicators: RecommendedIndicator[]
  count: number
}

// ═══ PR-4: 공유 라벨 상수 ═══

export const TYPE_LABELS: Record<string, string> = {
  market_data: '시장',
  macro: '매크로',
  sentiment: '심리',
  technical: '기술적',
  custom: '커스텀',
}

export const DIRECTION_LABELS: Record<string, { text: string; className: string }> = {
  positive: { text: '↑ 유리', className: 'text-blue-400 bg-blue-900/30' },
  negative: { text: '↑ 불리', className: 'text-orange-400 bg-orange-900/30' },
}

// ═══ 상태 아이콘 키 (v2 M6) ═══
// ThesisBadge에서 사용. lucide-react 컴포넌트와 1:1 매핑.
// 문자열 오타를 컴파일 타임에 잡기 위한 union type.
export type ThesisStateIconKey =
  | 'loader'
  | 'eye'
  | 'trending_up'
  | 'trending_down'
  | 'alert_triangle'
  | 'clock'
  | 'timer'
  | 'check_circle'
  | 'x_circle'
  | 'minus_circle'
