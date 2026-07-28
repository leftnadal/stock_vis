// Claim 마감 파생 유틸 단위 검증 (MON-CLOSE-UI Phase 2 §0.3)
import { describe, expect, it } from 'vitest'

import { frozenScore, outcomeToVerdict, summarizeClaimClosure } from '@/lib/monitor/closure'
import type { Claim } from '@/types/monitor'

function makeClaim(overrides: Partial<Claim> = {}): Claim {
  return {
    id: 'c1',
    monitor: 'm1',
    assertion: '주장',
    deadline: null,
    status: 'active',
    outcome: 'pending',
    proposed_verdict: null,
    resolved_by: null,
    factor_tags: [],
    retro_memo: '',
    closure_snapshot: null,
    scenario_type: 'new_entry',
    entry_price: null,
    target_price: null,
    stop_price: null,
    purchase_price: null,
    purchase_date: null,
    fair_value_low: null,
    fair_value_high: null,
    last_price_zone: null,
    entry_reached_at: null,
    zone_display: null,
    created_at: '2026-07-01T00:00:00Z',
    resolved_at: null,
    ...overrides,
  }
}

describe('summarizeClaimClosure', () => {
  it('Claim이 없으면 항상 진행 중(isFullyClosed=false)', () => {
    const summary = summarizeClaimClosure([])
    expect(summary).toEqual({
      total: 0,
      resolved: 0,
      isFullyClosed: false,
      lastResolvedClaim: null,
    })
  })

  it('전부 pending이면 진행 중', () => {
    const summary = summarizeClaimClosure([makeClaim({ id: 'a' }), makeClaim({ id: 'b' })])
    expect(summary.isFullyClosed).toBe(false)
    expect(summary.resolved).toBe(0)
  })

  it('일부만 resolved면 "n중 m 마감" 파생용 부분 카운트를 낸다', () => {
    const summary = summarizeClaimClosure([
      makeClaim({ id: 'a', outcome: 'validated', resolved_at: '2026-07-01T00:00:00Z' }),
      makeClaim({ id: 'b', outcome: 'pending' }),
      makeClaim({ id: 'c', outcome: 'pending' }),
    ])
    expect(summary.total).toBe(3)
    expect(summary.resolved).toBe(1)
    expect(summary.isFullyClosed).toBe(false)
  })

  it('전부 resolved면 마감(isFullyClosed=true)이고 가장 최근 resolved_at claim을 반환한다', () => {
    const summary = summarizeClaimClosure([
      makeClaim({ id: 'a', outcome: 'validated', resolved_at: '2026-07-01T00:00:00Z' }),
      makeClaim({ id: 'b', outcome: 'invalidated', resolved_at: '2026-07-05T00:00:00Z' }),
    ])
    expect(summary.isFullyClosed).toBe(true)
    expect(summary.resolved).toBe(2)
    expect(summary.lastResolvedClaim?.id).toBe('b')
  })
})

describe('outcomeToVerdict', () => {
  it('validated/partial/invalidated/inconclusive는 그대로 통과한다', () => {
    expect(outcomeToVerdict('validated')).toBe('validated')
    expect(outcomeToVerdict('partial')).toBe('partial')
    expect(outcomeToVerdict('invalidated')).toBe('invalidated')
    expect(outcomeToVerdict('inconclusive')).toBe('inconclusive')
  })

  it('pending은 방어적으로 inconclusive(중립)로 폴백한다', () => {
    expect(outcomeToVerdict('pending')).toBe('inconclusive')
  })
})

describe('frozenScore (P1.5 동결값 우선순위)', () => {
  it('resolved + closure_snapshot → 동결값 사용', () => {
    const claim = makeClaim({
      outcome: 'validated',
      resolved_at: '2026-07-10T00:00:00Z',
      closure_snapshot: { overall_score: 0.42, frozen_at: '2026-07-10T00:00:00Z', payload: {} },
    })
    expect(frozenScore(claim, 0.99)).toBe(0.42) // live 0.99 무시, 동결 0.42
  })

  it('closure_snapshot null인 resolved → live 폴백(방어)', () => {
    const claim = makeClaim({ outcome: 'validated', closure_snapshot: null })
    expect(frozenScore(claim, 0.7)).toBe(0.7)
  })

  it('claim null/undefined → live 폴백', () => {
    expect(frozenScore(null, 0.5)).toBe(0.5)
    expect(frozenScore(undefined, null)).toBeNull()
  })
})
