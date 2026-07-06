/**
 * MP2-TREND S1 — 공용 MultiLineTrendChart + 섹터 순위 궤적.
 *
 * 커버리지: E1 강조 기본 / E2 범례 토글 / E4 범위 토글 / E5 희박 / 리드아웃 pinLatest /
 *   플로팅 툴팁 부재 / 축 반전(rank 궤적, SectorTrajectory).
 * 차트 SVG(ResponsiveContainer 내부)는 jsdom 폭 0이라 미검증 — 토글·리드아웃·범례(외부 DOM)로 행위 검증.
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MultiLineTrendChart, type TrendSeries } from '@/components/charts/MultiLineTrendChart'
import { SectorTrajectory } from '@/app/market-pulse-v2/details/SectorTrajectory'
import type { SectorDetail } from '@/lib/api/marketPulseV2'

const DATES = ['2026-06-30', '2026-07-01', '2026-07-02', '2026-07-03', '2026-07-04']
function mkSeries(): TrendSeries[] {
  return [
    { key: 'XLK', label: '기술', points: DATES.map((d, i) => ({ date: d, value: 1 + (i % 2), note: `강도 +${i}` })) },
    { key: 'XLE', label: '에너지', points: DATES.map((d, i) => ({ date: d, value: 5 + (i % 3) })) },
    { key: 'XLF', label: '금융', points: DATES.map((d, i) => ({ date: d, value: 9 - (i % 2) })) },
  ]
}

describe('MultiLineTrendChart', () => {
  it('E1: 범례 전 시리즈 + 강조 기본만 리드아웃 표시', () => {
    render(<MultiLineTrendChart series={mkSeries()} emphasis={{ default: ['XLK'], legendToggle: true }} />)
    // 범례는 전 시리즈
    expect(screen.getByTestId('trend-legend-XLK')).toBeInTheDocument()
    expect(screen.getByTestId('trend-legend-XLF')).toBeInTheDocument()
    // 리드아웃은 강조(XLK)만
    expect(screen.getByTestId('trend-readout-XLK')).toBeInTheDocument()
    expect(screen.queryByTestId('trend-readout-XLE')).not.toBeInTheDocument()
  })

  it('E2: 범례 토글 → 리드아웃에 추가/제거', () => {
    render(<MultiLineTrendChart series={mkSeries()} emphasis={{ default: ['XLK'], legendToggle: true }} />)
    expect(screen.queryByTestId('trend-readout-XLF')).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId('trend-legend-XLF')) // 강조 추가
    expect(screen.getByTestId('trend-readout-XLF')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('trend-legend-XLK')) // 강조 제거
    expect(screen.queryByTestId('trend-readout-XLK')).not.toBeInTheDocument()
  })

  it('E4: 7↔30 범위 토글 active 전환', () => {
    render(<MultiLineTrendChart series={mkSeries()} ranges={[7, 30]} />)
    const b7 = screen.getByTestId('trend-range-7')
    const b30 = screen.getByTestId('trend-range-30')
    expect(b7.className).toContain('bg-slate-800') // 기본 7 active
    fireEvent.click(b30)
    expect(b30.className).toContain('bg-slate-800')
    expect(b7.className).not.toContain('bg-slate-800')
  })

  it('E5: 데이터 희박(≤2일) → "데이터 축적 중" 라벨', () => {
    const sparse: TrendSeries[] = [{ key: 'XLK', label: '기술', points: [{ date: '2026-07-03', value: 1 }, { date: '2026-07-04', value: 2 }] }]
    render(<MultiLineTrendChart series={sparse} />)
    expect(screen.getByTestId('trend-sparse')).toHaveTextContent('데이터 축적 중')
  })

  it('리드아웃 pinLatest: 짚지 않으면 최신일(07-04) 표시', () => {
    render(<MultiLineTrendChart series={mkSeries()} emphasis={{ default: ['XLK'] }} readout={{ pinLatest: true }} />)
    expect(screen.getByTestId('trend-readout')).toHaveTextContent('07-04')
  })

  it('플로팅 툴팁 부재: recharts Tooltip 미렌더', () => {
    const { container } = render(<MultiLineTrendChart series={mkSeries()} />)
    expect(container.querySelector('.recharts-tooltip-wrapper')).toBeNull()
  })
})

describe('SectorTrajectory (축 반전 rank 궤적)', () => {
  const payload: SectorDetail = {
    available: true,
    date: '2026-07-04',
    sectors: [
      { symbol: 'XLK', rel_strength: 2.1, momentum_1d: 0, momentum_5d: 0, momentum_20d: 0, flow_proxy: 0, rank: 1 },
      { symbol: 'XLE', rel_strength: -1.0, momentum_1d: 0, momentum_5d: 0, momentum_20d: 0, flow_proxy: 0, rank: 11 },
    ],
    cross_dispersion: 0.3,
    rotation_index: 1.1,
    sector_history: [
      { symbol: 'XLK', history: DATES.map((d, i) => ({ date: d, rel_strength: 2 + i * 0.1, rank: 1 })) },
      { symbol: 'XLE', history: DATES.map((d, i) => ({ date: d, rel_strength: -1, rank: 11 })) },
    ],
  }

  it('rank tickFormat("위") + leaders/laggards 강조 기본', () => {
    render(<SectorTrajectory payload={payload} />)
    expect(screen.getByTestId('sector-trajectory')).toBeInTheDocument()
    // 강조 기본 = leaders(XLK rank1) + laggards(XLE rank11) → 리드아웃에 "1위" 포함(rank tickFormat)
    const ro = screen.getByTestId('trend-readout')
    expect(ro).toHaveTextContent('위') // ${v}위 포맷 적용 증명
  })
})
