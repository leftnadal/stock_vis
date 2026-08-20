// D1-SCOREBOARD — 성적판 표시 헬퍼 (판정 문장·라벨) 단위 테스트.
import { describe, expect, it } from 'vitest'

import {
  fmtSignedPct,
  hitRatePct,
  sampleLabel,
  unscoreableLabelKo,
  verdictSentence,
} from '@/lib/scorecard/present'
import {
  sigHit,
  sigHold,
  sigMiss,
  sigNoTarget,
  sigPending,
  sigUnscoreable,
} from '@/lib/scorecard/fixtures'
import type { ScorecardBoard } from '@/types/scorecard'

describe('fmtSignedPct', () => {
  it('부호를 붙인다', () => {
    expect(fmtSignedPct(6.3)).toBe('+6.3%')
    expect(fmtSignedPct(-10)).toBe('-10.0%')
    expect(fmtSignedPct(null)).toBe('—')
  })
})

describe('hitRatePct', () => {
  it('표본 0이면 null', () => {
    expect(hitRatePct(0, 0)).toBeNull()
    expect(hitRatePct(1, 2)).toBe(50)
  })
})

describe('sampleLabel', () => {
  const base = (total: number): ScorecardBoard => ({
    sample_n: total,
    significance_threshold: 60,
    direction_hit: { hits: 0, total },
    avg_target_progress: null,
    cross_sectional_ic: null,
    cross_sectional_ic_reason: null,
  })
  it('임계 미만이면 참고용', () => {
    expect(sampleLabel(base(2))).toBe('참고용 (표본 2/60)')
  })
  it('임계 이상이면 유의', () => {
    expect(sampleLabel(base(60))).toBe('유의 표본')
  })
})

describe('unscoreableLabelKo', () => {
  it('사유별 한국어 매핑', () => {
    expect(unscoreableLabelKo('corporate_action')).toContain('분할')
    expect(unscoreableLabelKo('series_break')).toContain('단절')
    expect(unscoreableLabelKo('no_data')).toContain('데이터')
    expect(unscoreableLabelKo('unknown_x')).toContain('unknown_x')
    expect(unscoreableLabelKo(null)).toBe('채점 불가')
  })
})

describe('verdictSentence — 4 상태 + 강등 케이스', () => {
  it('상승 적중', () => {
    expect(verdictSentence(sigHit)).toBe('상승 전망 → +15.0% 상승 (적중)')
  })
  it('하락 빗나감(반대 방향 표기)', () => {
    expect(verdictSentence(sigMiss)).toBe('하락 전망이었으나 +6.3% 상승')
  })
  it('대기 D-day', () => {
    expect(verdictSentence(sigPending)).toContain('만기 D-24 대기 중')
    expect(verdictSentence(sigPending)).toContain('2026-09-13')
  })
  it('채점 불가 — 분할', () => {
    expect(verdictSentence(sigUnscoreable)).toContain('분할')
  })
  it('유지(hold) — 방향 판정 대상 아님', () => {
    expect(verdictSentence(sigHold)).toContain('방향 판정 대상 아님')
  })
  it('무목표가 — 강등 문장', () => {
    expect(verdictSentence(sigNoTarget)).toBe('목표가 미제시 → -10.0% 하락')
  })
})
