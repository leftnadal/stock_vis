// Monitor 허브 타입 (MON-P3, api/v1/monitor/ 계약 미러)

export type MonitorScope = 'market' | 'sector' | 'theme' | 'fund' | 'stock'
export type MonitorStatus = 'setting_up' | 'active' | 'paused' | 'archived'
export type MonitorState =
  | 'warming_up'
  | 'active'
  | 'strengthening'
  | 'weakening'
  | 'critical'
  | 'needs_review'
  | 'expired'
  | 'paused'

export type IndicatorType =
  | 'market_data'
  | 'macro'
  | 'sentiment'
  | 'technical'
  | 'custom'
export type SupportDirection = 'positive' | 'negative'

export type ClaimStatus = 'active' | 'resolved'
export type ClaimOutcome = 'pending' | 'validated' | 'invalidated' | 'inconclusive'

// BE 엔진(arrow_calculator·state_machine)이 산출한 파생 표시값 — FE는 렌더만.
export interface MonitorDisplay {
  degree: number // 0~180
  color: string // hex
  label: string // 화살표 라벨
  phase: 'full_moon' | 'waxing' | 'half_moon' | 'waning' | 'new_moon'
  phase_label: string
  phase_icon: string
}

export interface Monitor {
  id: string
  scope: MonitorScope
  target_ref: string
  name: string
  status: MonitorStatus
  current_state: MonitorState
  target_date_end: string | null
  resolved_label: string | null
  // 리스트 카드용 파생값 (list/detail에서 채워짐, create 응답은 null)
  latest_score: number | null
  display: MonitorDisplay | null
  indicator_count: number | null
  next_deadline: string | null
  has_claim: boolean
  // 파이프라인(엔진) 소유 파생값 — 사용자 입력 불가 (MON-P3-ALERT)
  close_suggested: boolean
  danger_streak: number
  created_at: string
  updated_at: string
}

export interface MonitorIndicator {
  id: string
  monitor: string
  name: string
  indicator_type: IndicatorType
  support_direction: SupportDirection
  weight: number
  source_key: string
  epsilon: number | null
  window: number | null
  decay: number | null
  is_active: boolean
  is_paused: boolean
  override_score: number | null
  created_at: string
  updated_at: string
}

export interface Claim {
  id: string
  monitor: string
  assertion: string
  deadline: string | null
  status: ClaimStatus
  outcome: ClaimOutcome
  created_at: string
  resolved_at: string | null
}

export interface WeakestLink {
  indicator_id: string
  indicator_name: string
  score: number
}

export interface EvaluateResult {
  monitor_id: string
  asof_date: string
  overall_score: number
  state: MonitorState
  state_changed: boolean
  reminder_needed: boolean
  data_coverage: number
  indicator_scores: Record<string, number>
  weakest_link: WeakestLink | null
  divergence: boolean
  bias_warning: { message: string } | null
  category_overlap: { message: string } | null
  snapshot_id: string
}

// Monitor 생성/수정 페이로드 (읽기 전용 필드 제외)
export interface MonitorInput {
  scope: MonitorScope
  target_ref: string
  name: string
  status?: MonitorStatus
  target_date_end?: string | null
}

// 지표 카탈로그 항목 (GET /monitor/catalog/)
export interface CatalogEntry {
  key: string
  name: string
  indicator_type: IndicatorType
  default_direction: SupportDirection
  source: string
  unit: string
  description: string
}

// ── 전이 알림 (MON-P3-ALERT, GET /monitor/alerts/) ──
// 억제(is_suppressed) 알림은 서버가 목록에서 이미 제외 → 개별 행에서 항상 false로 관측됨.
export interface AlertEvent {
  id: string
  monitor: string
  monitor_name: string
  target_ref: string
  from_state: MonitorState
  to_state: MonitorState
  from_label: string
  to_label: string
  asof: string
  score: number
  is_deterioration: boolean
  is_suppressed: boolean
  read: boolean
  created_at: string
}

// 헤더 벨 배지용 (GET /monitor/alerts/summary/) — 악화만 카운트.
export interface AlertSummary {
  unread_deterioration_count: number
}

// ── 상태밴드 스파크라인 (MON-P3-ALERT §6, GET /monitor/monitors/{id}/sparkline/) ──
export type SparklinePhase = 'full_moon' | 'waxing' | 'half_moon' | 'waning' | 'new_moon'

export interface SparklinePoint {
  asof: string
  score: number
}

// min/max는 score 정의역 [-1,1] 구간 — BE 엔진(score_to_phase)이 단일 출처, FE 하드코딩 금지.
export interface SparklineBand {
  phase: SparklinePhase
  label: string
  min: number
  max: number
}

export interface SparklineResponse {
  series: SparklinePoint[]
  bands: SparklineBand[]
  transitions: string[] // AlertEvent asof(ISO) 목록
  delta_5d: number | null // 계산값만 통과 — 표시는 회전 맵 트랙 몫(이번 트랙은 미표시)
  window: number
}
