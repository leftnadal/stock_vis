/**
 * MP2-SECTOR-CD Slice 2 — 모멘텀 모드 + 국면 스트립 테스트.
 *
 * recharts는 jsdom(0-width)서 SVG 미렌더 → MultiLineTrendChart를 mock해 전달 props 포착
 *   (baseline hline=서빙값·connectNulls=false·momentum 시리즈 검증). RegimeStrip은 실제 렌더.
 */
import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

// MultiLineTrendChart mock — 마지막 렌더 props 포착.
const chartCalls: any[] = []
vi.mock('@/components/charts/MultiLineTrendChart', () => ({
  MultiLineTrendChart: (props: any) => {
    chartCalls.push(props)
    return <div data-testid="mock-trend-chart" />
  },
}))

import type { SectorDetail as Detail } from '@/lib/api/marketPulseV2'
import { SectorTrajectory } from '@/app/market-pulse-v2/details/SectorTrajectory'
import { buildSegments, RegimeStrip } from '@/app/market-pulse-v2/details/RegimeStrip'

function lastChart() {
  return chartCalls[chartCalls.length - 1]
}

const LABELS: Record<string, string> = {
  'sector.XLK': '기술',
  'sector.XLE': '에너지',
  'regime.LATE_BULL': '후기강세',
  'regime.CRISIS': '위기',
}

function mkPayload(baseline?: number): Detail {
  return {
    available: true,
    date: '2026-07-09',
    cross_dispersion: 0.8,
    rotation_index: 1.5,
    cd_momentum_baseline: baseline,
    sectors: [
      { symbol: 'XLK', rel_strength: 1.0, momentum_1d: 0, momentum_5d: 0.5, momentum_20d: 0, flow_proxy: 0, rank: 1 },
      { symbol: 'XLE', rel_strength: -1.0, momentum_1d: 0, momentum_5d: -0.5, momentum_20d: 0, flow_proxy: 0, rank: 2 },
    ],
    sector_history: [
      {
        symbol: 'XLK',
        history: [
          { date: '2026-07-07', rel_strength: 1.0, rank: 1, momentum_5d: 0.3 },
          { date: '2026-07-08', rel_strength: 1.2, rank: 1, momentum_5d: null },
          { date: '2026-07-09', rel_strength: 1.0, rank: 1, momentum_5d: 0.5 },
        ],
      },
      {
        symbol: 'XLE',
        history: [
          { date: '2026-07-07', rel_strength: -1.0, rank: 2, momentum_5d: -0.4 },
          { date: '2026-07-09', rel_strength: -1.0, rank: 2, momentum_5d: -0.5 },
        ],
      },
    ],
  }
}

const REGIME_HISTORY = [
  { date: '2026-07-07', stage: 'LATE_BULL' },
  { date: '2026-07-08', stage: 'LATE_BULL' },
  { date: '2026-07-09', stage: 'CRISIS' },
]

describe('SectorTrajectory — 모드 토글', () => {
  it('디폴트 = 순위 모드(기존 동작 무영향)', () => {
    chartCalls.length = 0
    const { getByTestId } = render(<SectorTrajectory payload={mkPayload(0)} labels={LABELS} />)
    expect(getByTestId('traj-mode-rank').getAttribute('aria-selected')).toBe('true')
    expect(getByTestId('traj-mode-momentum').getAttribute('aria-selected')).toBe('false')
    // 순위 차트 = y축 반전(rank)
    expect(lastChart().yAxis.inverted).toBe(true)
  })

  it('모멘텀 탭 클릭 → 모멘텀 시리즈 + connectNulls=false + baseline hline(서빙값)', () => {
    chartCalls.length = 0
    const { getByTestId } = render(<SectorTrajectory payload={mkPayload(0)} labels={LABELS} regimeHistory={REGIME_HISTORY} />)
    fireEvent.click(getByTestId('traj-mode-momentum'))
    const chart = lastChart()
    // connectNulls 금지(규칙 3-2)
    expect(chart.connectNulls).toBe(false)
    // baseline hline = 서빙된 cd_momentum_baseline(규칙 #3, 하드코딩 아님)
    expect(chart.overlays.hlines).toEqual([{ value: 0, label: '판정선' }])
    // y축 비반전(모멘텀)
    expect(chart.yAxis.inverted).toBeUndefined()
  })

  it('baseline hline은 서빙 값을 그대로 사용(하드코딩 0 아님)', () => {
    chartCalls.length = 0
    // 실제 baseline은 0이나, FE가 서빙값을 쓰는지 증명 위해 구별되는 값 주입
    const { getByTestId } = render(<SectorTrajectory payload={mkPayload(1.5)} labels={LABELS} />)
    fireEvent.click(getByTestId('traj-mode-momentum'))
    expect(lastChart().overlays.hlines).toEqual([{ value: 1.5, label: '판정선' }])
  })

  it('baseline 미서빙 → hline 생략(발명 금지)', () => {
    chartCalls.length = 0
    const { getByTestId } = render(<SectorTrajectory payload={mkPayload(undefined)} labels={LABELS} />)
    fireEvent.click(getByTestId('traj-mode-momentum'))
    expect(lastChart().overlays.hlines).toEqual([])
  })

  it('모멘텀 시리즈는 null momentum_5d 점 제외(선 끊김 → connectNulls=false)', () => {
    chartCalls.length = 0
    const { getByTestId } = render(<SectorTrajectory payload={mkPayload(0)} labels={LABELS} />)
    fireEvent.click(getByTestId('traj-mode-momentum'))
    const xlk = lastChart().series.find((s: any) => s.key === 'XLK')
    // XLK는 07-08 momentum null → 2점만(07-07, 07-09)
    expect(xlk.points.map((p: any) => p.date)).toEqual(['2026-07-07', '2026-07-09'])
    expect(xlk.points.every((p: any) => typeof p.value === 'number')).toBe(true)
  })

  it('순위↔모멘텀 왕복 전환', () => {
    const { getByTestId } = render(<SectorTrajectory payload={mkPayload(0)} labels={LABELS} />)
    fireEvent.click(getByTestId('traj-mode-momentum'))
    expect(getByTestId('traj-mode-momentum').getAttribute('aria-selected')).toBe('true')
    fireEvent.click(getByTestId('traj-mode-rank'))
    expect(getByTestId('traj-mode-rank').getAttribute('aria-selected')).toBe('true')
  })
})

describe('RegimeStrip — 국면 스트립', () => {
  it('모멘텀 모드 + regimeHistory → 스트립 렌더(구간)', () => {
    const { getByTestId, queryByTestId } = render(
      <SectorTrajectory payload={mkPayload(0)} labels={LABELS} regimeHistory={REGIME_HISTORY} />,
    )
    // 순위 모드엔 스트립 없음
    expect(queryByTestId('regime-strip')).toBeNull()
    fireEvent.click(getByTestId('traj-mode-momentum'))
    expect(getByTestId('regime-strip')).toBeInTheDocument()
    // LATE_BULL 구간 + CRISIS 구간
    expect(getByTestId('strip-seg-LATE_BULL')).toBeInTheDocument()
    expect(getByTestId('strip-seg-CRISIS')).toBeInTheDocument()
  })

  it('regimeHistory 없으면 스트립 미렌더', () => {
    const { getByTestId, queryByTestId } = render(<SectorTrajectory payload={mkPayload(0)} labels={LABELS} />)
    fireEvent.click(getByTestId('traj-mode-momentum'))
    expect(queryByTestId('regime-strip')).toBeNull()
  })

  it('buildSegments — 연속 동일 국면 run-length', () => {
    const dates = ['d1', 'd2', 'd3', 'd4', 'd5']
    const byDate = new Map([
      ['d1', 'LATE_BULL'],
      ['d2', 'LATE_BULL'],
      ['d3', 'CRISIS'],
      ['d4', 'CRISIS'],
      ['d5', 'CRISIS'],
    ])
    const segs = buildSegments(dates, byDate)
    expect(segs).toEqual([
      { stage: 'LATE_BULL', count: 2, startDate: 'd1' },
      { stage: 'CRISIS', count: 3, startDate: 'd3' },
    ])
  })

  it('buildSegments — 미매핑 날짜는 unknown 구간', () => {
    const segs = buildSegments(['d1', 'd2'], new Map([['d1', 'CRISIS']]))
    expect(segs).toEqual([
      { stage: 'CRISIS', count: 1, startDate: 'd1' },
      { stage: 'unknown', count: 1, startDate: 'd2' },
    ])
  })

  it('RegimeStrip 직접 — 빈 dates/regimeHistory graceful(null)', () => {
    const { container } = render(<RegimeStrip dates={[]} regimeHistory={REGIME_HISTORY} />)
    expect(container.firstChild).toBeNull()
  })
})
