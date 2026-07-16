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
export type ClaimOutcome =
  | 'pending'
  | 'validated'
  | 'partial'
  | 'invalidated'
  | 'inconclusive'
  | 'expired' // 기한만료 (D-TIMING-DECISIONS-5 ④-B)

// 마감 시 사용자가 고를 수 있는 최종 판정 (inconclusive 제외 — 엣지). expired = 시스템 제안·선택 가능.
export type ProposedVerdict = 'validated' | 'partial' | 'invalidated' | 'expired'
// VerdictBadge 등 표시용 — ProposedVerdict + inconclusive(중립 표시).
export type Verdict = ProposedVerdict | 'inconclusive'

// 가격 구간축 (BE Claim.PriceZone 미러 — TIMING-P1).
export type PriceZone = 'exited' | 'entry' | 'approach' | 'waiting' | 'overheated'

// zone_display (serializer, BE 완결 표시 메타 — FE 재계산 금지). 가격 3필드 없으면 null.
export interface ZoneDisplay {
  zone: PriceZone | null
  label: string | null
  close: number | null
  boundaries: {
    stop: number
    entry: number
    approach_ceiling: number
    target: number
  }
}

// L계열 가격 제안 (GET /monitor/scenario-suggest/?symbol=).
export interface ScenarioSuggest {
  available: boolean
  symbol: string
  close?: number
  support_low?: number
  entry_suggest?: number
  atr?: number | null
  stop_suggest?: number | null
  basis?: string
}
// 회고 공통 요인 태그 (고정 enum — BE Claim.FactorTag 미러).
export type FactorTag = 'timing' | 'ext_shock' | 'indicator_noise' | 'luck'
// 지표별 마감 결과 (BE ClaimIndicatorResult.Result 미러).
export type IndicatorResultValue = 'hit' | 'partial' | 'miss' | 'na'

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
  // 마감 회고 (MON-CLOSE-UI Phase 1) — 전부 close 액션에서만 채워짐(마감 전 null/빈값).
  proposed_verdict: ProposedVerdict | null
  resolved_by: number | null // user id만 옴 — 마감자=소유자=현재 뷰어(owner-scoping)
  factor_tags: FactorTag[]
  retro_memo: string
  // 마감 동결 스냅샷 (MON-CLOSE-UI P1.5) — resolved면 동결값, PENDING이면 null.
  closure_snapshot: ClosureSnapshotData | null
  // 매수 시나리오 가격 (TIMING-P1, DRF Decimal→문자열). 무가격 구 가설이면 전부 null.
  entry_price: string | null
  target_price: string | null
  stop_price: string | null
  fair_value_low: string | null
  fair_value_high: string | null
  // 가격 구간축 (파이프라인 소유·read-only) + BE 완결 표시 메타.
  last_price_zone: PriceZone | null
  entry_reached_at: string | null
  zone_display: ZoneDisplay | null
  created_at: string
  resolved_at: string | null
}

// 마감 시점 불변 동결값 (BE ClosureSnapshot 노출). 동결 점수·지표·달 위상 표시 소스.
export interface ClosureSnapshotData {
  overall_score: number
  frozen_at: string
  payload: Record<string, unknown>
}

// GET /monitor/claims/{id}/close-preview/ — 마감 모달 프리필(무상태, 읽기 전용).
export interface ClosePreviewIndicator {
  id: string
  name: string
  latest_value: number | null
}

export interface ClosePreview {
  proposed_verdict: ProposedVerdict
  overall_score: number
  indicators: ClosePreviewIndicator[]
}

// POST /monitor/claims/{id}/close/ 요청 바디.
export interface IndicatorResultInput {
  indicator_id: string
  result: IndicatorResultValue
}

export interface CloseClaimInput {
  final_verdict: ProposedVerdict
  factor_tags: FactorTag[]
  retro_memo?: string
  indicator_results: IndicatorResultInput[]
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

// 지표 카탈로그 항목 (GET /monitor/catalog/). S계열 6종은 신규 메타 포함(TIMING-P1).
export type EvidenceStrength = 'strong' | 'medium' | 'weak'

export interface CatalogEntry {
  key: string
  name: string
  indicator_type: IndicatorType
  default_direction: SupportDirection
  source: string
  unit: string
  description: string
  // S계열 전용 메타 (기존 3종은 undefined).
  evidence_strength?: EvidenceStrength
  scoring_mode?: 'zscore' | 'bounded'
  default_selected?: boolean
  compute_key?: string
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
