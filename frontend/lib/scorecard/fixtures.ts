// D1-SCOREBOARD — 성적판 테스트 fixtures (4 신호 상태 전부 + 표본 라벨).
// 적중·빗나감·대기 D-day·채점 불가 + hold/무목표가 강등 케이스 커버.
import type { AnalystScorecard, ScorecardSignal } from '@/types/scorecard'

export const sigHit: ScorecardSignal = {
  direction: 'up',
  captured_at: '2026-07-01',
  spot_at_capture: 100,
  target_price: 120,
  maturity_date: '2026-07-30',
  status: 'scored',
  realized: { close: 115, return_pct: 15, target_progress_pct: 75, verdict: 'hit' },
  unscoreable_reason: null,
  pending_d_day: null,
  cohort: 'pinned',
}

export const sigMiss: ScorecardSignal = {
  direction: 'down',
  captured_at: '2026-07-02',
  spot_at_capture: 200,
  target_price: 180,
  maturity_date: '2026-07-31',
  status: 'scored',
  realized: { close: 212.6, return_pct: 6.3, target_progress_pct: -63, verdict: 'miss' },
  unscoreable_reason: null,
  pending_d_day: null,
  cohort: 'pinned',
}

export const sigPending: ScorecardSignal = {
  direction: 'up',
  captured_at: '2026-08-15',
  spot_at_capture: 50,
  target_price: 60,
  maturity_date: '2026-09-13',
  status: 'pending',
  realized: null,
  unscoreable_reason: null,
  pending_d_day: 24,
  cohort: 'pinned',
}

export const sigUnscoreable: ScorecardSignal = {
  direction: 'up',
  captured_at: '2026-06-01',
  spot_at_capture: 30,
  target_price: 40,
  maturity_date: null,
  status: 'unscoreable',
  realized: null,
  unscoreable_reason: 'corporate_action',
  pending_d_day: null,
  cohort: 'pinned',
}

export const sigHold: ScorecardSignal = {
  direction: 'flat',
  captured_at: '2026-07-05',
  spot_at_capture: 90,
  target_price: 90,
  maturity_date: '2026-08-03',
  status: 'scored',
  realized: { close: 93.6, return_pct: 4, target_progress_pct: null, verdict: 'flat' },
  unscoreable_reason: null,
  pending_d_day: null,
  cohort: 'pinned',
}

export const sigNoTarget: ScorecardSignal = {
  direction: null,
  captured_at: '2026-07-06',
  spot_at_capture: 70,
  target_price: null,
  maturity_date: '2026-08-04',
  status: 'scored',
  realized: { close: 63, return_pct: -10, target_progress_pct: null, verdict: 'flat' },
  unscoreable_reason: null,
  pending_d_day: null,
  cohort: 'derived',
}

export const scorecardFixture: AnalystScorecard = {
  as_of: '2026-08-20',
  horizon: 21,
  reproduction: {
    as_of: '2026-08-20',
    scoring_version: 1,
    git_head: 'abc1234',
    input_rows: { ass_rows: 139, daily_price_rows: 5354 },
    splits_input_rows: 15,
    splits_max_date: '2024-06-10',
    computed_at: '2026-08-20T10:30:00+09:00',
  },
  board: {
    sample_n: 4,
    significance_threshold: 60,
    direction_hit: { hits: 1, total: 2 },
    avg_target_progress: 6,
    cross_sectional_ic: null,
    cross_sectional_ic_reason: '표본 미도달 — 최초 만기 2026-09-01',
  },
  symbols: [
    {
      symbol: 'AAPL',
      counts: { scored: 1, pending: 1, unscoreable: 0 },
      hit: { hits: 1, total: 1 },
      avg_target_progress: 75,
      signals: [sigHit, sigPending],
    },
    {
      symbol: 'TSLA',
      counts: { scored: 1, pending: 0, unscoreable: 0 },
      hit: { hits: 0, total: 1 },
      avg_target_progress: -63,
      signals: [sigMiss],
    },
    {
      symbol: 'NVDA',
      counts: { scored: 0, pending: 0, unscoreable: 1 },
      hit: null,
      avg_target_progress: null,
      signals: [sigUnscoreable],
    },
    {
      symbol: 'GOOGL',
      counts: { scored: 2, pending: 0, unscoreable: 0 },
      hit: null,
      avg_target_progress: null,
      signals: [sigHold, sigNoTarget],
    },
  ],
}

// 전건 pending(라이브 현 상태) — board 빈 집계.
export const scorecardAllPending: AnalystScorecard = {
  ...scorecardFixture,
  board: {
    sample_n: 0,
    significance_threshold: 60,
    direction_hit: { hits: 0, total: 0 },
    avg_target_progress: null,
    cross_sectional_ic: null,
    cross_sectional_ic_reason: '표본 미도달 — 최초 만기 2026-09-01',
  },
  symbols: [
    {
      symbol: 'AAPL',
      counts: { scored: 0, pending: 1, unscoreable: 0 },
      hit: null,
      avg_target_progress: null,
      signals: [sigPending],
    },
  ],
}

// 심볼 0 (빈 상태).
export const scorecardEmpty: AnalystScorecard = {
  ...scorecardFixture,
  board: {
    sample_n: 0,
    significance_threshold: 60,
    direction_hit: { hits: 0, total: 0 },
    avg_target_progress: null,
    cross_sectional_ic: null,
    cross_sectional_ic_reason: '표본 미도달',
  },
  symbols: [],
}
