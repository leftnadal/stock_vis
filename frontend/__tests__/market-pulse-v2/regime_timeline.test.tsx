/**
 * MP-UX-S4 Part A — Regime 국면 타임라인 렌더 회귀.
 *
 * 세그먼트 병합 / width / 전환 방향(STAGE_ORDER) / 엣지(단일·짧음·미지enum) graceful.
 * 색·순서·전환문구는 meaning.ts 단일소스. 백엔드 무관(순수 FE).
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { RegimeHistoryPoint } from '@/lib/api/marketPulseV2'
import {
  RegimeTimeline,
  groupSegments,
} from '@/app/market-pulse-v2/details/RegimeTimeline'

const KO = {
  'regime.BULL_EXPANSION': '강세 확장',
  'regime.LATE_BULL': '상승 후반 경계',
  'regime.TRANSITION': '전환',
}

function hist(stages: string[]): RegimeHistoryPoint[] {
  // date 오름차순 (2026-06-01 + i일)
  return stages.map((s, i) => ({
    date: `2026-06-${String(i + 1).padStart(2, '0')}`,
    stage: s as RegimeHistoryPoint['stage'],
  }))
}

describe('groupSegments', () => {
  it('연속 동일 병합 + width = count/total', () => {
    const segs = groupSegments(hist(['BULL_EXPANSION', 'BULL_EXPANSION', 'BULL_EXPANSION', 'TRANSITION', 'TRANSITION']))
    expect(segs).toHaveLength(2)
    expect(segs[0].count).toBe(3)
    expect(segs[0].widthPct).toBeCloseTo(60)
    expect(segs[1].count).toBe(2)
    expect(segs[1].widthPct).toBeCloseTo(40)
  })

  it('짧은 데이터(5개) → total=5로 계산 (가짜 0 패딩 없음)', () => {
    const segs = groupSegments(hist(['LATE_BULL', 'LATE_BULL', 'TRANSITION', 'TRANSITION', 'TRANSITION']))
    expect(segs[0].widthPct).toBeCloseTo(40)
    expect(segs[1].widthPct).toBeCloseTo(60)
    expect(segs.reduce((s, x) => s + x.count, 0)).toBe(5)
  })

  it('단일 단계 → 세그먼트 1개', () => {
    expect(groupSegments(hist(Array(30).fill('LATE_BULL')))).toHaveLength(1)
  })
})

describe('RegimeTimeline 렌더', () => {
  it('전환 방향 개선: TRANSITION → LATE_BULL = 상향(개선)', () => {
    render(<RegimeTimeline history={hist([...Array(4).fill('TRANSITION'), ...Array(15).fill('LATE_BULL')])} labels={KO} />)
    expect(screen.getByText(/상향\(개선\)/)).toBeInTheDocument()
    expect(screen.getByText(/전환 → 상승 후반 경계/)).toBeInTheDocument()
  })

  it('전환 방향 악화: LATE_BULL → TRANSITION = 하향(악화)', () => {
    render(<RegimeTimeline history={hist([...Array(10).fill('LATE_BULL'), ...Array(5).fill('TRANSITION')])} labels={KO} />)
    expect(screen.getByText(/하향\(악화\)/)).toBeInTheDocument()
  })

  it('단일 단계 30일 → "유지" 주석, 전환 문구 없음', () => {
    render(<RegimeTimeline history={hist(Array(30).fill('LATE_BULL'))} labels={KO} />)
    expect(screen.getByText(/30일간 상승 후반 경계 유지/)).toBeInTheDocument()
    expect(screen.queryByText(/상향|하향/)).not.toBeInTheDocument()
  })

  it('빈 history → graceful 메시지', () => {
    render(<RegimeTimeline history={[]} labels={KO} />)
    expect(screen.getByText('국면 이력 데이터 없음')).toBeInTheDocument()
  })

  it('미지 enum → crash 0 + raw 라벨 fallback + console.warn', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(() =>
      render(<RegimeTimeline history={hist(['WEIRD_STAGE', 'WEIRD_STAGE'])} labels={KO} />),
    ).not.toThrow()
    // 범례에 raw enum(번역 불가) 노출
    expect(screen.getAllByText('WEIRD_STAGE').length).toBeGreaterThan(0)
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })
})
