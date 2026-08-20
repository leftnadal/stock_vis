// D1-SCOREBOARD — 애널리스트 성적판 타입 (BE compute-on-read 계약 hand-author).
// scorecard 엔드포인트 serializer는 passthrough 앵커라 openapi 생성 타입이 없다
// → BE analyst_scoring.build_scorecard 계약을 여기 단일 소스로 유지(승격 이사 전제).

export type SignalStatus = 'scored' | 'pending' | 'unscoreable'
export type SignalDirection = 'up' | 'down' | 'flat' | null
export type SignalVerdict = 'hit' | 'miss' | 'flat'

export interface ScorecardRealized {
  close: number
  return_pct: number | null
  target_progress_pct: number | null
  verdict: SignalVerdict
}

export interface ScorecardSignal {
  direction: SignalDirection
  captured_at: string
  spot_at_capture: number | null
  target_price: number | null
  maturity_date: string | null
  status: SignalStatus
  realized: ScorecardRealized | null
  unscoreable_reason: string | null
  pending_d_day: number | null
  cohort: string
}

export interface ScorecardSymbol {
  symbol: string
  counts: { scored: number; pending: number; unscoreable: number }
  hit: { hits: number; total: number } | null
  avg_target_progress: number | null
  signals: ScorecardSignal[]
}

export interface ScorecardBoard {
  sample_n: number
  significance_threshold: number
  direction_hit: { hits: number; total: number }
  avg_target_progress: number | null
  cross_sectional_ic: number | null
  cross_sectional_ic_reason: string | null
}

export interface ScorecardReproduction {
  as_of: string
  scoring_version: number
  git_head: string
  input_rows: Record<string, number>
  splits_input_rows: number | null
  splits_max_date: string | null
  computed_at?: string
}

export interface AnalystScorecard {
  as_of: string
  horizon: number
  reproduction: ScorecardReproduction
  board: ScorecardBoard
  symbols: ScorecardSymbol[]
}
