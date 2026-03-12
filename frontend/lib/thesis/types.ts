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
  source_entry: string           // 'news' | 'free_input' | 'popular' | 'template' | 'chainsight'
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
  current_arrow_degree: number   // 0 ~ 180
  current_label: string
  current_color: string          // hex 색상 코드
  is_active: boolean
  premise: string | null         // premise id
}

export interface ThesisAlert {
  id: string
  thesis: string                 // thesis id
  indicator: string | null       // ThesisIndicator id, 지표 무관 알림이면 null
  alert_type: string             // 'indicator_change' | 'threshold_cross' | 'news_event' | 'target_date' | 'daily_summary'
  title: string
  message: string
  is_read: boolean
  created_at: string
}

// ═══ API 응답 ═══

export interface DashboardResponse {
  thesis: Thesis
  premises: (ThesisPremise & { indicators: ThesisIndicator[] })[]
  recent_alerts: ThesisAlert[]
  moon_phase: {
    phase: string                // 'full_moon' | 'waxing' | 'half_moon' | 'waning' | 'new_moon'
    label: string
  }
  overall_score: number          // -1.0 ~ 1.0
}

export interface ConversationButton {
  id: string
  label: string
  type?: 'text_input'
  long_press_hint?: boolean
}

export interface ConversationResponse {
  message: string
  buttons: ConversationButton[]
  selection_mode: 'single' | 'multi'
  long_press_explanations?: Record<string, string>
  conversation_state: string
  step: number
  total_steps: number
  thesis?: Thesis                // 가설 완성 시 포함
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
