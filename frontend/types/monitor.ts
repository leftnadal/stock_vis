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

// 시나리오 모드 (BE Claim.ScenarioType 미러 — HOLD-P1).
export type ScenarioType = 'new_entry' | 'hold' | 'add_on'

// 사다리 밴드/틱 (BE zone_display 완결 — FE 하드코딩 제거, HOLD-P1).
export interface ZoneBand {
  key: string
  tone: PriceZone // ZONE_TONE 조회 키
  active: boolean
}
export interface ZoneTick {
  label: string
  value: number
}

// zone_display (serializer, BE 완결 표시 메타 — FE 재계산 금지). 가격 3필드 없으면 null.
// bands/ticks/rows/marker/pnl 전부 BE 단일 소스(HOLD-P1). ?는 하위호환(구 응답 폴백 허용).
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
  // ── HOLD-P1 additive ──
  mode?: ScenarioType
  mode_label?: string | null
  pnl_pct?: number | null // hold: (close/purchase−1)×100
  stop_distance_pct?: number | null // 손절여유(%): (close−stop)/close×100 (MON-DETAIL-P1 T1a). close 없으면 null
  marker_fraction?: number | null // 현재가 위치 0~1
  anchor_fraction?: number | null // hold 매입가 마커 0~1 (new_entry는 null)
  bands?: ZoneBand[] // 색 밴드(new_entry 5·hold 4)
  ticks?: ZoneTick[] // 미니 사다리 하단 라벨
  rows?: ZoneTick[] // 수직 사다리 우측 라벨(위→아래)
}

// 정합 재계산 블록 (TIMING-P2.5) — 힌트용, 자동 개서 아님.
export interface Coherence {
  symbol: string
  sigma: number | null
  note: string
  basis?: string
  coherent_horizon_days?: number
  coherent_deadline?: string
  coherent_target?: string
  rr?: number | null
  error?: string
}

// L계열 가격 제안 + 정합 프리필 (GET /monitor/scenario-suggest/?symbol=).
// mode=hold + purchase_price 제공 시 보유 프리필(매입가·진입가 미제안 + 본전 회복 N주).
export interface ScenarioSuggest {
  available: boolean
  symbol: string
  mode?: ScenarioType
  close?: number
  support_low?: number
  resistance_high?: number
  entry_suggest?: number
  atr?: number | null
  sigma?: number | null
  stop_suggest?: number | null
  target_suggest?: number | null
  horizon_days?: number | null
  deadline_suggest?: string | null
  rr_suggest?: number | null
  omit?: string | null
  // ── hold 전용 ──
  purchase_price?: number
  in_profit?: boolean
  breakeven_weeks?: number | null
  captions?: {
    entry?: string | null
    stop?: string | null
    target?: string | null
    deadline?: string | null
    breakeven?: string | null
  }
  basis?: string
  // entry + (target|deadline) 쿼리 제공 시에만 (재계산)
  coherence?: Coherence
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
  // MON-P2A T3: 점수 커버리지 {유효, 전체}(예 6/9). 스냅샷/annotation 없으면 null.
  indicator_coverage: { sufficient: number; total: number } | null
  next_deadline: string | null
  has_claim: boolean
  // 파이프라인(엔진) 소유 파생값 — 사용자 입력 불가 (MON-P3-ALERT)
  close_suggested: boolean
  danger_streak: number
  created_at: string
  updated_at: string
  // 통화 표시 계약 (PART B-FE 숫자 표시 규약 '가') — BE가 채워줌, 없으면 FE는 'USD' 폴백.
  currency_code?: string
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
  // 시나리오 모드 (HOLD-P1). 기존 데이터 default=new_entry.
  scenario_type: ScenarioType
  // 매수 시나리오 가격 (TIMING-P1, DRF Decimal→문자열). 무가격 구 가설이면 전부 null.
  entry_price: string | null
  target_price: string | null
  stop_price: string | null
  // 보유 확정 사실 (HOLD-P1) — hold 모드에서만 채워짐.
  purchase_price: string | null
  purchase_date: string | null
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
  is_sufficient?: boolean // MON-P2A T3: 신호 패널 sufficient 배지 소스
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

// ── 점수 정본 시계열 (MON-P2B T1, GET /monitor/monitors/{id}/snapshots/) ──
// MonitorSnapshot(동결 기록) 기반 — 스트립 델타·일지 스냅샷의 단일 원천.
// sparkline(추세 곡선, 재산출)과 별개 소스 — 혼동 금지.
export interface SnapshotSeriesPoint {
  asof: string
  score: number
  delta: number | null // 직전 스냅샷 대비 Δ (전체 첫 점만 null, ±0도 유효값)
}

export interface SnapshotSeriesResponse {
  series: SnapshotSeriesPoint[]
  window: number
}

// ── ADVISOR 브리핑 일지 (MON-P4-LA T3, GET /monitor/monitors/{id}/advisor_notes/) ──
// surface=L-A 한정, 최신순(asof desc, BE order_by('-asof')). 일지 kind=advisor 소스.
export interface AdvisorNote {
  id: string
  asof: string
  surface: string
  headline: string
  body: string
  coverage_n: number
  coverage_total: number
  model_id: string
  prompt_version: string
  created_at: string
}

// ── Claim 근거 (RECON-SWAP-0813 PART 1, /monitor/claim-evidences/) ──
// BE ClaimEvidence 미러 — 자동형(kind=auto, 지표 z 임계 대조)·수동형(kind=manual, 서술+재확인) 단일 테이블.
export type EvidenceKind = 'auto' | 'manual'
export type EvidenceOperator = 'gte' | 'lte' | 'gt' | 'lt'

export interface ClaimEvidence {
  id: string
  claim: string
  kind: EvidenceKind
  // 자동형 전용(수동형은 전부 null)
  indicator: string | null
  operator: EvidenceOperator | null
  threshold: number | null
  grace_days: number
  // 수동형 전용(자동형은 description=''·recheck_period_days=기본값)
  description: string
  recheck_period_days: number
  last_confirmed_at: string | null
  created_at: string
}

// POST /monitor/claim-evidences/ 요청 바디(모드별 필수값은 BE validate가 최종 판정).
export interface ClaimEvidenceInput {
  claim: string
  kind: EvidenceKind
  indicator?: string | null
  operator?: EvidenceOperator | null
  threshold?: number | null
  grace_days?: number
  description?: string
  recheck_period_days?: number
  last_confirmed_at?: string | null
}

// GET /monitor/claims/{id}/evidence-status/?as_of= — 근거 생사 판정(계약층, 읽기 전용·상태변경 없음).
export type EvidenceLifeStatus = 'alive' | 'dead' | 'expired' | 'unknown'

export interface EvidenceStatusResult {
  evidence_id: string
  kind: EvidenceKind
  status: EvidenceLifeStatus
  dead_streak_days: number
  indicator_name: string | null
  description: string
}

export interface EvidenceStatusResponse {
  claim_id: string
  as_of: string
  total: number
  alive: number
  results: EvidenceStatusResult[]
}

// ── 교체 검토 보류 이력 (RECON-SWAP-0813 PART 3-BE, /monitor/swap-hold-logs/) ──
// 횟수·누적일수는 이 로그를 조회 측(FE)이 집계한다 — 별도 카운터 없음(BE 단일 소스=로그).
export interface SwapHoldLog {
  id: string
  claim: string
  held_at: string
  candidate_ref: string | null
  // 보류 시점 가격 스냅샷 (P-1 성과 앵커, DRF Decimal→문자열). 구 기록(스냅샷 신설 이전)은 null.
  hold_price: string | null
  candidate_price: string | null
  note: string
  // PART C-4: BE 서버 산출 성과(held_at 스냅샷 → 최신 종가, DailyPrice 기반). 가격 이력·후보
  // 미지정이면 null — FE는 존재하면 우선 소비하고 없으면 Wallet 현재가 계산으로 폴백한다.
  hold_performance_pct?: number | null
  candidate_performance_pct?: number | null
}

export interface SwapHoldLogInput {
  claim: string
  candidate_ref?: string | null
  hold_price?: string | null
  candidate_price?: string | null
  note?: string
}

// ── 결정 일지 (RECON-SWAP-0813 PART 3-BE, /monitor/decision-journal-entries/) ──
// 마감/재커밋 실행 시 강제되는 1문장. sentence 품질 검증 없음(ADR §6 — 최소 글자수 등 FE도 금지).
export type DecisionJournalKind = 'close' | 'recommit' | 'hold'

export interface DecisionJournalEntry {
  id: string
  claim: string
  kind: DecisionJournalKind
  sentence: string
  created_at: string
}

export interface DecisionJournalEntryInput {
  claim: string
  kind: DecisionJournalKind
  sentence: string
}
