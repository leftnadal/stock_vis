// Claim 마감 파생 유틸 단위 검증 (MON-CLOSE-UI Phase 2 §0.3)
import { describe, expect, it } from 'vitest'

import { outcomeToVerdict, summarizeClaimClosure } from '@/lib/monitor/closure'
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
