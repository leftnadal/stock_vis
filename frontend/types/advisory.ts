// Advisory(권유) 읽기 화면 타입 — apps/portfolio/schemas/advisory_contract.py 1:1 미러.
//
// ⚠ codegen 대체 사유: gen:advisory-schema(spectacular)는 정상 실행되지만, 응답 스키마가
// `OpenApiSerializerExtension.target_class`("portfolio.api.advisory.*")가 실제 모듈
// 경로("apps.portfolio.api.advisory.*")와 어긋나(PR7 apps/ 이동 후 미수정 추정 — coach도
// 동일 접두어라 재현 확인, 현재 재생성 시 coach 쪽도 "No response body"로 텅 빔) 응답 바디가
// 비어 나온다. 이 파일은 Pydantic 계약(advisory_contract.py)을 수기 미러해 drift 0을 보장한다.
// 코드젠 인프라 수정은 본 슬라이스 범위 밖(백엔드 소관) — 발견 사실만 보고.
//
// ★ 값 규약: 모든 Decimal은 `_jsonable`로 문자열 직렬화된다 (금액·비율 전부 string).
// score는 "배치 우선순위 점수"이며 기대수익률이 아니다(§2 절대 규칙).

export type AdvisoryMode = 'BUY' | 'DEFEND'
export type AdvisoryTrigger = 'auto' | 'manual'
export type RecommendationAction = 'BUY' | 'HOLD' | 'TRIM'
export type RecommendationLane = 'core' | 'exploration'

export interface Recommendation {
  action: RecommendationAction
  symbol: string
  currency: string
  score: string | null // BUY=배치 우선순위 점수(str), HOLD/TRIM=null. 기대수익 아님.
  lane: RecommendationLane
  rationale: string
}

export interface DialByCurrency {
  cash_krw: string
  buffer_share_krw: string
  deployable_krw: string
  headroom_ratio: string
}

export interface Dial {
  dd: string
  a: string
  buffer: string
  is_new_high: boolean
  headroom_frac: string
  deployable_krw_total: string
  frozen: boolean
  window_days: number
  by_currency: Record<string, DialByCurrency>
}

export interface Knobs {
  A: number
  G: number
  w: string
  L: number
  E: number
}

export interface MaxConcentration {
  symbol: string
  currency: string
  weight: string
}

export interface ProgressGap {
  return_pct: string
  gap_pct: string
  cost_krw: string
  value_krw: string
  by_currency: Record<string, { cost_krw: string; value_krw: string }>
  cost_labels?: Record<string, number>
}

export interface AllocationGap {
  cash_krw: string
  holdings_value_krw: string
  idle_ratio: string
  by_currency: Record<string, { cash_krw: string; holdings_value_krw: string }>
}

export interface AdvisorySummary {
  goal_target_return_pct?: string | null
  numeraire: 'KRW'
  cost_basis_note: string
  dial: Dial
  knobs: Knobs
  max_concentration?: MaxConcentration | null
  notes: string[]
  progress_gap: ProgressGap
  allocation_gap: AllocationGap
  fx_context: Record<string, unknown>
}

export interface AdvisoryOutput {
  mode: AdvisoryMode
  summary: AdvisorySummary
  recommendations: Recommendation[]
  disclaimer: string
}

// GET /advisory/latest/, POST /advisory/run/
export interface LatestAdvisory {
  available: boolean
  trigger: AdvisoryTrigger | null
  run_at: string | null
  output: AdvisoryOutput | null
}

// GET /advisory/summary/
export interface AssetSummary {
  available: boolean
  date?: string
  total_krw?: string
  by_currency?: Record<string, unknown>
  price_as_of?: string
  progress_gap?: Record<string, unknown>
  allocation_gap?: Record<string, unknown>
  mode?: AdvisoryMode
}

// GET /advisory/knobs/ — 읽기 전용(쓰기는 20b)
export interface KnobsRead {
  available: boolean
  aggressiveness_offset?: number
  growth_boost?: number
  diversification_weight?: string
  concentration_limit?: number
  exploration_ratio?: number
}
