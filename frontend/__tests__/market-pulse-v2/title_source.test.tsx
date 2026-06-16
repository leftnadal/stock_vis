/**
 * MP-UX-TITLE-SOURCE(C) — "레짐/국면" 표시 용어 단일소스 통일 회귀 테스트.
 *
 * 검증:
 *   1. 단일 상수 REGIME_TERM = '국면' (단일 진실)
 *   2. 전 사용처(카드/타임라인/상세 에러)에서 "레짐" 미출현, "국면" 일치
 *   3. 상수 1곳 참조로 전파 — REGIME_TERM을 쓰면 모든 표시가 같이 바뀜
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { RegimeCard, RegimeHistoryPoint } from '@/lib/api/marketPulseV2'
import { REGIME_TERM } from '@/app/market-pulse-v2/meaning'
import { RegimeCardSummary } from '@/app/market-pulse-v2/cards/RegimeCardSummary'
import { RegimeTimeline } from '@/app/market-pulse-v2/details/RegimeTimeline'

describe('REGIME_TERM 단일소스', () => {
  it('표시 용어는 "국면"으로 통일', () => {
    expect(REGIME_TERM).toBe('국면')
  })
})

describe('전 사용처 용어 일치 ("레짐" 미출현)', () => {
  it('RegimeCardSummary 데이터 미생성 → "국면 데이터 미생성"(레짐 0)', () => {
    render(<RegimeCardSummary data={null} />)
    expect(screen.getByText(`${REGIME_TERM} 데이터 미생성`)).toBeInTheDocument()
    expect(screen.queryByText(/레짐/)).not.toBeInTheDocument()
  })

  it('RegimeCardSummary 타이틀 → "시장 국면"', () => {
    const data: RegimeCard = {
      regime: 'BULL_EXPANSION', status: 'OK', coverage: 0.9, headline: '', fired_rules: [], transitioned: false,
    }
    render(<RegimeCardSummary data={data} />)
    expect(screen.getByText(`시장 ${REGIME_TERM}`)).toBeInTheDocument()
  })

  it('RegimeTimeline 빈 이력 → "국면 이력 데이터 없음"(레짐 0)', () => {
    render(<RegimeTimeline history={[]} />)
    expect(screen.getByText(`${REGIME_TERM} 이력 데이터 없음`)).toBeInTheDocument()
    expect(screen.queryByText(/레짐/)).not.toBeInTheDocument()
  })

  it('RegimeTimeline 헤더 → "최근 N일 국면"', () => {
    const history: RegimeHistoryPoint[] = [
      { date: '2026-06-10', stage: 'BULL_EXPANSION' },
      { date: '2026-06-11', stage: 'BULL_EXPANSION' },
    ]
    render(<RegimeTimeline history={history} />)
    expect(screen.getByText(`최근 ${history.length}일 ${REGIME_TERM}`)).toBeInTheDocument()
  })
})
