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

export interface Monitor {
  id: string
  scope: MonitorScope
  target_ref: string
  name: string
  status: MonitorStatus
  current_state: MonitorState
  target_date_end: string | null
  resolved_label: string | null
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
