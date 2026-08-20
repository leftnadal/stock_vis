// 대결 화면 순수 로직 검증 (RECON-SWAP-0813 PART 3-B) — 마찰/판단불가/반론/보류 계기판.
import { describe, expect, it } from 'vitest'

import {
  buildCounterArgument,
  checkJudgmentAvailability,
  computeHoldGaugePerformance,
  estimateFriction,
  summarizeEvidenceStatus,
  summarizeHoldGauge,
} from '@/lib/monitor/duel'
import { manualExpiryDday } from '@/lib/monitor/evidence'
import type { EvidenceStatusResponse, SwapHoldLog } from '@/types/monitor'

describe('estimateFriction', () => {
  it('미보유(가격 없음)면 unheld를 반환한다', () => {
    const r = estimateFriction(null, null)
    expect(r.direction).toBe('unheld')
    expect(r.unrealizedPct).toBeNull()
  })

  it('평가이익 상태면 cost 방향(어림 문구 포함)을 반환한다', () => {
    const r = estimateFriction('100', '120')
    expect(r.direction).toBe('cost')
    expect(r.unrealizedPct).toBeCloseTo(20)
    expect(r.note).toContain('어림')
  })

  it('평가손실 상태면 relief 방향을 반환한다', () => {
    const r = estimateFriction('100', '80')
    expect(r.direction).toBe('relief')
    expect(r.unrealizedPct).toBeCloseTo(-20)
  })

  it('손익 중립(±1% 이내)이면 neutral을 반환한다', () => {
    const r = estimateFriction('100', '100.5')
    expect(r.direction).toBe('neutral')
  })
})

describe('checkJudgmentAvailability', () => {
  it('Claim이 없으면 판단 불가', () => {
    const r = checkJudgmentAvailability({ hasClaim: false, evidenceTotal: 0, unknownCount: 0 })
    expect(r.available).toBe(false)
    expect(r.reasons.length).toBeGreaterThan(0)
    expect(r.nextConditions.length).toBeGreaterThan(0)
  })

  it('근거가 0건이면 판단 불가', () => {
    const r = checkJudgmentAvailability({ hasClaim: true, evidenceTotal: 0, unknownCount: 0 })
    expect(r.available).toBe(false)
  })

  it('판정불가 근거가 절반 이상이면 판단 불가', () => {
    const r = checkJudgmentAvailability({ hasClaim: true, evidenceTotal: 4, unknownCount: 2 })
    expect(r.available).toBe(false)
  })

  it('Claim+근거+낮은 unknown 비율이면 판단 가능', () => {
    const r = checkJudgmentAvailability({ hasClaim: true, evidenceTotal: 4, unknownCount: 1 })
    expect(r.available).toBe(true)
    expect(r.reasons).toHaveLength(0)
  })
})

describe('buildCounterArgument', () => {
  it('근거 0건이면 "관측 근거 없음" 사실을 포함한다', () => {
    const r = buildCounterArgument({
      sideLabel: '보유',
      evidenceTotal: 0,
      evidenceAlive: 0,
      manualCount: 0,
      deadOrExpiredCount: 0,
      gapMultiplier: 1,
      friction: 'neutral',
    })
    expect(r.facts.join(' ')).toContain('관측 근거')
  })

  it('수동형 비중이 높으면 수동 의존도 사실을 포함한다', () => {
    const r = buildCounterArgument({
      sideLabel: '보유',
      evidenceTotal: 4,
      evidenceAlive: 4,
      manualCount: 3,
      deadOrExpiredCount: 0,
      gapMultiplier: 1,
      friction: 'neutral',
    })
    expect(r.facts.some((f) => f.includes('수동형'))).toBe(true)
  })

  it('facts는 최대 3개로 고정된다(동분량 보장)', () => {
    const r = buildCounterArgument({
      sideLabel: '보유',
      evidenceTotal: 4,
      evidenceAlive: 1,
      manualCount: 3,
      deadOrExpiredCount: 3,
      gapMultiplier: 2,
      friction: 'cost',
    })
    expect(r.facts.length).toBeLessThanOrEqual(3)
  })
})

describe('summarizeEvidenceStatus', () => {
  it('undefined 입력이면 전부 0을 반환한다', () => {
    const r = summarizeEvidenceStatus(undefined)
    expect(r).toEqual({ total: 0, alive: 0, manualCount: 0, unknownCount: 0, deadOrExpiredCount: 0 })
  })

  it('kind/status로 정확히 집계한다', () => {
    const status: EvidenceStatusResponse = {
      claim_id: 'c1',
      as_of: '2026-08-11',
      total: 3,
      alive: 1,
      results: [
        { evidence_id: 'e1', kind: 'auto', status: 'alive', dead_streak_days: 0, indicator_name: 'X', description: '' },
        { evidence_id: 'e2', kind: 'manual', status: 'expired', dead_streak_days: 10, indicator_name: null, description: 'd' },
        { evidence_id: 'e3', kind: 'auto', status: 'unknown', dead_streak_days: 0, indicator_name: 'Y', description: '' },
      ],
    }
    const r = summarizeEvidenceStatus(status)
    expect(r).toEqual({ total: 3, alive: 1, manualCount: 1, unknownCount: 1, deadOrExpiredCount: 1 })
  })
})

describe('summarizeHoldGauge', () => {
  it('로그 0건이면 count=0, cumulativeDays=null', () => {
    const r = summarizeHoldGauge([])
    expect(r).toEqual({ count: 0, firstHeldAt: null, cumulativeDays: null })
  })

  it('1건이면 cumulativeDays는 null(2회째부터 표시)', () => {
    const logs: SwapHoldLog[] = [
      {
        id: '1',
        claim: 'c1',
        held_at: '2026-08-01T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: null,
        candidate_price: null,
        note: '',
      },
    ]
    const r = summarizeHoldGauge(logs)
    expect(r.count).toBe(1)
    expect(r.cumulativeDays).toBeNull()
  })

  it('2건 이상이면 cumulativeDays를 최초 held_at 기준으로 산출한다', () => {
    const logs: SwapHoldLog[] = [
      {
        id: '2',
        claim: 'c1',
        held_at: '2026-08-05T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: null,
        candidate_price: null,
        note: '',
      },
      {
        id: '1',
        claim: 'c1',
        held_at: '2026-08-01T00:00:00Z',
        candidate_ref: 'MSFT',
        hold_price: null,
        candidate_price: null,
        note: '',
      },
    ]
    const r = summarizeHoldGauge(logs)
    expect(r.count).toBe(2)
    expect(r.firstHeldAt).toBe('2026-08-01T00:00:00Z')
    expect(r.cumulativeDays).not.toBeNull()
  })
})

describe('computeHoldGaugePerformance', () => {
  function log(overrides: Partial<SwapHoldLog>): SwapHoldLog {
    return {
      id: '1',
      claim: 'c1',
      held_at: '2026-08-01T00:00:00Z',
      candidate_ref: 'MSFT',
      hold_price: null,
      candidate_price: null,
      note: '',
      ...overrides,
    }
  }

  it('로그가 1건 이하면 전부 null을 반환한다(2회째부터 표시 원칙과 동일)', () => {
    const r = computeHoldGaugePerformance([log({})], '110', '55')
    expect(r).toEqual({
      holdPerformancePct: null,
      holdPerformanceReason: null,
      candidatePerformancePct: null,
      candidatePerformanceReason: null,
      gapPct: null,
    })
  })

  it('최초 로그(최초 held_at) 스냅샷 대비 현재가로 양측 성과·격차를 산출한다', () => {
    const logs: SwapHoldLog[] = [
      log({
        id: '2',
        held_at: '2026-08-05T00:00:00Z',
        hold_price: '105',
        candidate_price: '52',
      }),
      // 정렬 검증용 — held_at이 더 이른 이 로그가 앵커가 되어야 한다
      log({
        id: '1',
        held_at: '2026-08-01T00:00:00Z',
        hold_price: '100',
        candidate_price: '50',
      }),
    ]
    const r = computeHoldGaugePerformance(logs, '110', '55')
    expect(r.holdPerformancePct).toBeCloseTo(10)
    expect(r.candidatePerformancePct).toBeCloseTo(10)
    expect(r.gapPct).toBeCloseTo(0)
    expect(r.holdPerformanceReason).toBeNull()
    expect(r.candidatePerformanceReason).toBeNull()
  })

  it('격차 = 보유 성과 − 후보 성과(부호 포함)', () => {
    const logs: SwapHoldLog[] = [
      log({ hold_price: '100', candidate_price: '100' }),
      log({ id: '2', held_at: '2026-08-05T00:00:00Z' }),
    ]
    const r = computeHoldGaugePerformance(logs, '120', '90')
    expect(r.holdPerformancePct).toBeCloseTo(20)
    expect(r.candidatePerformancePct).toBeCloseTo(-10)
    expect(r.gapPct).toBeCloseTo(30)
  })

  it('스냅샷 이전 구 기록(가격 null)이면 anchor_missing으로 정직 표기한다', () => {
    const logs: SwapHoldLog[] = [
      log({ hold_price: null, candidate_price: null }),
      log({ id: '2', held_at: '2026-08-05T00:00:00Z' }),
    ]
    const r = computeHoldGaugePerformance(logs, '110', '55')
    expect(r.holdPerformancePct).toBeNull()
    expect(r.holdPerformanceReason).toBe('anchor_missing')
    expect(r.candidatePerformancePct).toBeNull()
    expect(r.candidatePerformanceReason).toBe('anchor_missing')
    expect(r.gapPct).toBeNull()
  })

  it('앵커는 있으나 현재가 소스가 없으면(후보 미보유) no_current_price로 표기한다', () => {
    const logs: SwapHoldLog[] = [
      log({ hold_price: '100', candidate_price: '50' }),
      log({ id: '2', held_at: '2026-08-05T00:00:00Z' }),
    ]
    const r = computeHoldGaugePerformance(logs, '110', undefined)
    expect(r.holdPerformancePct).toBeCloseTo(10)
    expect(r.candidatePerformancePct).toBeNull()
    expect(r.candidatePerformanceReason).toBe('no_current_price')
    expect(r.gapPct).toBeNull()
  })
})

describe('manualExpiryDday', () => {
  it('last_confirmed_at + recheck_period_days 기준으로 D-n을 계산한다', () => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const future = new Date(today)
    future.setDate(future.getDate() + 10)
    const pad = (n: number) => String(n).padStart(2, '0')
    const lastConfirmed = `${future.getFullYear()}-${pad(future.getMonth() + 1)}-${pad(future.getDate())}`
    const d = manualExpiryDday({
      last_confirmed_at: lastConfirmed,
      recheck_period_days: 0,
      created_at: '2026-01-01T00:00:00Z',
    })
    expect(d).toBe(10)
  })

  it('last_confirmed_at이 없으면 created_at을 기준으로 삼는다', () => {
    const d = manualExpiryDday({
      last_confirmed_at: null,
      recheck_period_days: 90,
      created_at: '2020-01-01T00:00:00Z',
    })
    // 아주 오래 전 기준일 + 90일 → 이미 만료(음수)
    expect(d).toBeLessThan(0)
  })
})
