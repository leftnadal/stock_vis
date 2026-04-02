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
  ai_summary: string             // Phase 3: AI 분석 텍스트 (PR-10에서 채움)
  notable_changes: NotableChange[] // Phase 3: 오늘의 변화 목록
  snapshot_date: string | null   // 스냅샷 기준일 (ISO date)
}

/** 분기 지표 히스토리 포인트 */
export interface QuarterlyPoint {
  fy: number
  fq: number
  value: number
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
  // Phase 3: 실제 값
  raw_value: number | null
  raw_value_unit: string         // '$', '원', '%', 'pt', ''
  previous_raw_value: number | null
  change_pct: number | null
  raw_value_asof: string | null  // 데이터 기준일 (ISO datetime)
  // 분기 지표 확장 (BE-PR-2)
  fiscal_label: string | null           // "2025 Q3" 또는 "2024 FY"
  quarterly_history: QuarterlyPoint[] | null  // 최근 4분기 히스토리
  is_quarterly: boolean                 // metrics 소스 여부
  comparison_type: 'qoq' | 'yoy' | null  // 비교 타입
  // 지표 설명 + 가설 관계성
  description: string                   // 카탈로그 기반 지표 설명
  recommendation_reason: string         // 이 가설에 추천된 이유
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

// ═══ LLM 빌더 Phase (Phase A-MVP) ═══

export type BuilderPhase = 'suggestions' | 'proposal' | 'preset' | 'confirm' | 'complete' | 'fallback'

// ═══ 가설 제안 (Suggestion Mode) ═══

export interface ThesisSuggestionPremise {
  title: string
  description?: string
  recommended_indicators?: Array<{
    indicator_db_id?: number
    why: string
    signal_type?: string
  }>
}

export interface ThesisSuggestion {
  direction: 'bullish' | 'bearish'
  title: string
  summary: string
  target: string
  target_type: string
  thesis_type: string[]
  premises: ThesisSuggestionPremise[]
}

export interface SuggestResponse {
  conversation_state: ConversationState
  suggestions: ThesisSuggestion[]
  phase: BuilderPhase
  entry_mode: 'suggestions' | 'fallback_start'
}

// ═══ 대화 상태 (백엔드 conversation_state echo) ═══

export interface ConversationState {
  conv_id: string
  entry_source: EntrySource
  step: number
  collected: Record<string, unknown>
  source_news_id?: string
  // LLM mode extensions
  mode?: 'llm' | 'wizard'
  phase?: BuilderPhase
  history?: Array<{ role: 'user' | 'assistant'; content: string }>
  turn_count?: number
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

// ═══ LLM 빌더 지표 추천 (Phase A-MVP) ═══

export interface LLMIndicatorRecommendation {
  premise_title: string
  indicator_name: string
  why: string
  signal_type: 'leading' | 'coincident' | 'lagging'
  auto_matched: boolean
  match_method: 'pk' | 'text'
  indicator?: { id: number; [key: string]: unknown }
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
  // LLM mode extensions
  phase?: BuilderPhase
  confidence?: 'high' | 'medium' | 'low'
  needs_preset?: boolean
  indicator_recommendations?: LLMIndicatorRecommendation[]
  is_complete?: boolean
  created_thesis?: {
    thesis_id: string
    title: string
    dashboard_url: string
  }
  fallback_reason?: string
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

// ═══ Phase 3: Dashboard 리디자인 — 실제 값 확장 ═══

/** alert_engine 이벤트 기반 변화 기록 */
export interface NotableChange {
  indicator_id: string
  indicator_name: string
  change_type: 'sharp_move' | 'direction_flip' | 'threshold_cross' | 'streak'
  description: string
  raw_value_before: number | null
  raw_value_after: number | null
  change_pct: number | null
  severity: 'info' | 'warning'
}

/** 차트용 시계열 포인트 */
export interface IndicatorReadingPoint {
  asof: string
  value: number | null
  raw_value: number | null
}

/** Readings API 응답 */
export interface IndicatorReadingsResponse {
  indicator_id: string
  indicator_name: string
  support_direction: SupportDirection
  unit: string
  readings: IndicatorReadingPoint[]
  count: number
}

/** 차트 기간 타입 */
export type ChartPeriod = 7 | 14 | 30

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
