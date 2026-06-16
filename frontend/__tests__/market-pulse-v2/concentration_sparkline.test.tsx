/**
 * MP-UX-S5 Part B — 집중도 30일 스파크라인 회귀 테스트.
 *
 * 검증:
 *   1. sparkPoints: 값 배열 → 정규화 폴리라인 좌표(가짜 0 패딩 0)
 *   2. concentrationTrend: 마지막 vs 처음 추세, 2점 미만 → null
 *   3. 렌더: history 있을 때 추세 주석, 1점 graceful(추세 보류)
 *   4. ConcentrationDetail: history_30d 없을 때 스파크라인 미렌더(합성 0)
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { ConcentrationDetail as Detail, ConcentrationHistoryPoint } from '@/lib/api/marketPulseV2'
import { concentrationTrend } from '@/app/market-pulse-v2/meaning'
import { ConcentrationSparkline, sparkPoints } from '@/app/market-pulse-v2/details/ConcentrationSparkline'
import { ConcentrationDetail } from '@/app/market-pulse-v2/details/ConcentrationDetail'

function hp(date: string, top10: number): ConcentrationHistoryPoint {
  return { date, top5: top10 * 0.7, top10, hhi: 0.05 }
}

describe('sparkPoints', () => {
  it('빈 배열 → 빈 문자열(합성 0)', () => {
    expect(sparkPoints([])).toBe('')
  })
  it('N점 → N좌표 쌍', () => {
    const pts = sparkPoints([0.3, 0.35, 0.4], 200, 40)
    expect(pts.split(' ')).toHaveLength(3)
  })
  it('최소값이 바닥(큰 y), 최대값이 천장(작은 y) — 정규화', () => {
    const pts = sparkPoints([0.3, 0.4], 200, 40, 3).split(' ')
    const y0 = Number(pts[0].split(',')[1]) // 0.3 = 최소 → 바닥(y 큰 값)
    const y1 = Number(pts[1].split(',')[1]) // 0.4 = 최대 → 천장(y 작은 값)
    expect(y0).toBeGreaterThan(y1)
  })
})

describe('concentrationTrend', () => {
  it('증가 → up', () => {
    expect(concentrationTrend([0.3, 0.35, 0.42])).toBe('up')
  })
  it('감소 → down', () => {
    expect(concentrationTrend([0.42, 0.35, 0.3])).toBe('down')
  })
  it('변화 미미(epsilon 안쪽) → flat', () => {
    expect(concentrationTrend([0.4, 0.401, 0.405])).toBe('flat')
  })
  it('2점 미만 → null', () => {
    expect(concentrationTrend([0.4])).toBeNull()
    expect(concentrationTrend([])).toBeNull()
  })
})

describe('ConcentrationSparkline 렌더', () => {
  const history = [hp('2026-05-13', 0.3), hp('2026-06-11', 0.42)]

  it('추세 주석 + 현재 밴드 노출', () => {
    render(<ConcentrationSparkline history={history} />)
    expect(screen.getByText(/쏠림 심화 ↑/)).toBeInTheDocument()
    expect(screen.getByText(/현재 강한 쏠림/)).toBeInTheDocument()
  })

  it('1점 데이터 → 추세 보류(graceful)', () => {
    render(<ConcentrationSparkline history={[hp('2026-06-11', 0.42)]} />)
    expect(screen.getByText(/추세 산출 보류/)).toBeInTheDocument()
  })

  it('빈 history → "이력 데이터 없음"(합성 0)', () => {
    render(<ConcentrationSparkline history={[]} />)
    expect(screen.getByText('집중도 이력 데이터 없음')).toBeInTheDocument()
  })
})

describe('ConcentrationDetail — 스파크라인 통합', () => {
  const base: Detail = {
    available: true,
    date: '2026-06-11',
    universe: 'SPY',
    top5_weight: 0.28,
    top10_weight: 0.41,
    hhi: 0.0521,
    top_holdings: [{ symbol: 'AAPL', weight: 0.071 }],
  }

  it('history_30d 있으면 스파크라인 렌더', () => {
    render(<ConcentrationDetail payload={{ ...base, history_30d: [hp('2026-05-13', 0.3), hp('2026-06-11', 0.42)] }} />)
    expect(screen.getByText(/상위10 비중 추세/)).toBeInTheDocument()
  })

  it('history_30d 없으면 스파크라인 미렌더(합성 0)', () => {
    render(<ConcentrationDetail payload={base} />)
    expect(screen.queryByText(/상위10 비중 추세/)).not.toBeInTheDocument()
  })
})
