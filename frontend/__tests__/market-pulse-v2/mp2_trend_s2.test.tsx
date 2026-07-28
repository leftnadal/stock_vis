/**
 * MP2-TREND S2 — 전환일 세로선 + 기준선(MA20) 이탈 리드아웃 + 델타 강조 복원.
 *
 * 커버리지: E1 breadth 리드아웃(기준선 대비 % + streak) / E2 이탈 마커 폴백(리드아웃 streak) /
 *   E4 전환일 0건 graceful / E5 델타 행 탭→강조 인자 / E5b emphasisOverride 반영 /
 *   E5c 인자 없는 진입 무영향 / E6 섹터 전환일 세로선(overlays 공용) + 파생 helper.
 * 차트 SVG(ResponsiveContainer 내부)는 jsdom 폭 0이라 미검증 — 리드아웃·콜백(외부 DOM)·순수 helper로 행위 검증.
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { BreadthTrajectory } from '@/app/market-pulse-v2/details/BreadthTrajectory'
import { SectorTrajectory } from '@/app/market-pulse-v2/details/SectorTrajectory'
import { DeltaCard } from '@/app/market-pulse-v2/cards/DeltaCard'
import {
  baselineDistancePct,
  baselineNote,
  deviationStartDate,
  transitionVlines,
} from '@/app/market-pulse-v2/details/trendOverlays'
import type { BreadthDetail, SectorDetail, SectorDelta } from '@/lib/api/marketPulseV2'

const DATES = ['2026-06-30', '2026-07-01', '2026-07-02', '2026-07-03', '2026-07-04']

function mkBreadth(): BreadthDetail {
  // A/D선이 기준선(MA20) 아래로 이탈. 최신일 −184, 기준선 −180.7 → −1.8%, 4일째 이탈.
  return {
    available: true,
    ma_deviation_streak_days: 4,
    history_30d: [
      { date: DATES[0], advance: 0, decline: 0, ad_line: -100, ad_line_change: 0, ad_line_ma20: -95 },
      { date: DATES[1], advance: 0, decline: 0, ad_line: -140, ad_line_change: 0, ad_line_ma20: -130 },
      { date: DATES[2], advance: 0, decline: 0, ad_line: -160, ad_line_change: 0, ad_line_ma20: -150 },
      { date: DATES[3], advance: 0, decline: 0, ad_line: -170, ad_line_change: 0, ad_line_ma20: -165 },
      { date: DATES[4], advance: 0, decline: 0, ad_line: -184, ad_line_change: 0, ad_line_ma20: -180.7 },
    ],
  }
}

function mkSector(): SectorDetail {
  return {
    available: true,
    date: DATES[4],
    sectors: [
      { symbol: 'XLK', rel_strength: 2.1, momentum_1d: 0, momentum_5d: 0, momentum_20d: 0, flow_proxy: 0, rank: 1 },
      { symbol: 'XLE', rel_strength: -1.0, momentum_1d: 0, momentum_5d: 0, momentum_20d: 0, flow_proxy: 0, rank: 11 },
    ],
    cross_dispersion: 0.3,
    rotation_index: 1.1,
    sector_history: [
      { symbol: 'XLK', history: DATES.map((d) => ({ date: d, rel_strength: 2, rank: 1 })) },
      { symbol: 'XLE', history: DATES.map((d) => ({ date: d, rel_strength: -1, rank: 11 })) },
    ],
  }
}

describe('MP2-TREND S2 — 파생 helper (순수)', () => {
  it('baselineDistancePct: 서빙된 두 값의 단순 차(%), ma 없으면 null', () => {
    expect(baselineDistancePct(-184, -180.7)).toBeCloseTo(-1.826, 2)
    expect(baselineDistancePct(100, null)).toBeNull()
    expect(baselineDistancePct(100, 0)).toBeNull()
  })

  it('baselineNote: 기준선 대비 % + 최신 streak 부기', () => {
    expect(baselineNote(-184, -180.7, 4)).toBe('기준선 대비 −1.8% · 4일째 이탈')
    expect(baselineNote(-184, -180.7)).toBe('기준선 대비 −1.8%')
    expect(baselineNote(100, null, 0)).toBeUndefined()
  })

  it('deviationStartDate: streak가 시작된 날짜(마커 폴백), streak 0이면 null', () => {
    const hist = DATES.map((d) => ({ date: d }))
    expect(deviationStartDate(hist, 4)).toBe(DATES[1]) // 5개 중 마지막 4개 시작 = idx1
    expect(deviationStartDate(hist, 0)).toBeNull()
  })

  it('E6/E4: transitionVlines — 라벨 "국면 전환 MM-DD", 빈 배열 graceful', () => {
    expect(transitionVlines(['2026-07-02'])).toEqual([{ date: '2026-07-02', label: '국면 전환 07-02' }])
    expect(transitionVlines([])).toEqual([])
    expect(transitionVlines()).toEqual([])
  })
})

describe('MP2-TREND S2 — BreadthTrajectory (E1/E2/E4)', () => {
  it('E1/E2: 리드아웃에 "기준선 대비 −1.8% · 4일째 이탈"(이탈 마커 폴백 = streak 표기)', () => {
    render(<BreadthTrajectory payload={mkBreadth()} />)
    const ro = screen.getByTestId('trend-readout')
    expect(ro).toHaveTextContent('기준선 대비')
    expect(ro).toHaveTextContent('4일째 이탈')
  })

  it('E4: 전환일 0건 + 빈 데이터 graceful (오류 없이 렌더)', () => {
    // transitionDates 미전달 → 세로선 0. 정상 렌더.
    expect(() => render(<BreadthTrajectory payload={mkBreadth()} transitionDates={[]} />)).not.toThrow()
    expect(screen.getByTestId('breadth-trajectory')).toBeInTheDocument()
    // 데이터 없음 → empty 상태
    render(<BreadthTrajectory payload={{ available: true, history_30d: [] }} />)
    expect(screen.getByTestId('breadth-trajectory-empty')).toBeInTheDocument()
  })
})

describe('MP2-TREND S2 — 델타 강조 복원 (E5)', () => {
  const deltas: SectorDelta[] = [
    { sector: 'XLE', rank: 3, prev_rank: 7, rank_delta: 4, as_of: '2026-07-04', vs_date: '2026-07-03' },
    { sector: 'XLK', rank: 1, prev_rank: 2, rank_delta: 1, as_of: '2026-07-04', vs_date: '2026-07-03' },
  ]

  it('E5: 델타 섹터 행 탭 → onOpenTrajectory가 해당 섹터 강조 인자로 호출', () => {
    const onOpen = vi.fn()
    render(<DeltaCard regime={null} sectorDeltas={deltas} onOpenTrajectory={onOpen} />)
    const rows = screen.getAllByTestId('sector-row')
    fireEvent.click(rows[0]) // XLE 행
    expect(onOpen).toHaveBeenCalledTimes(1)
    const arg = onOpen.mock.calls[0][0]
    expect(arg).toContain('XLE') // 탭한 섹터가 강조 인자에 포함(델타 상위와 union)
  })

  it('E5b: emphasisOverride 전달 시 궤적 뷰가 그 섹터를 기본 강조(리드아웃 반영)', () => {
    // XLE만 override → 리드아웃에 에너지 라벨(fallback=심볼) 노출, XLK는 미노출.
    render(<SectorTrajectory payload={mkSector()} emphasisOverride={['XLE']} />)
    expect(screen.getByTestId('trend-readout-XLE')).toBeInTheDocument()
    expect(screen.queryByTestId('trend-readout-XLK')).not.toBeInTheDocument()
  })

  it('E5c: emphasisOverride 없으면 기존 기본(leaders/laggards) 유지 — 무영향', () => {
    render(<SectorTrajectory payload={mkSector()} />)
    // leaders(XLK rank1) + laggards(XLE rank11) 둘 다 강조 → 리드아웃에 양쪽 존재
    expect(screen.getByTestId('trend-readout-XLK')).toBeInTheDocument()
    expect(screen.getByTestId('trend-readout-XLE')).toBeInTheDocument()
  })
})
