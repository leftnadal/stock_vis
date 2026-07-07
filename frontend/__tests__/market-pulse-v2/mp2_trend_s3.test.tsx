/**
 * MP2-TREND S3(R1) — 국면 재료 판정-거리 소형 다중.
 *
 * 커버리지: E1 7칸 그리드+현재값/거리 / E2 컷 hlines(payload 추종, 하드코딩 0) /
 *   E3 "⚠ 컷 통과" / E4 세그먼트 컨트롤(raw↔z placeholder) / E5 기존 소비처 무영향(hlines) /
 *   E6 히스테리시스 캡션.
 * ※ 스크럽류(E3'): jsdom 0폭 SVG 한계 — 순수 payload 기반 셀 렌더로 간접 검증(사유: recharts
 *   onMouseMove 미발화, S2 관행). 컷/시계열은 mock payload 그대로 소비(하드코딩 없음).
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RegimeComponents } from '@/app/market-pulse-v2/details/RegimeComponents'
import { MultiLineTrendChart, type TrendSeries } from '@/components/charts/MultiLineTrendChart'
import type { RegimeComponent, RegimeDetail } from '@/lib/api/marketPulseV2'

const DATES = ['2026-06-30', '2026-07-01', '2026-07-02', '2026-07-03', '2026-07-04']

function mkComponent(over: Partial<RegimeComponent>): RegimeComponent {
  return {
    key: 'vix',
    unit: '',
    current: 22.4,
    series: DATES.map((d, i) => ({ date: d, value: 20 + i })),
    cuts: [
      { value: 20, regime: 'LATE_BULL', op: '>' },
      { value: 25, regime: 'TRANSITION', op: '>=' },
      { value: 30, regime: 'BEAR_CONTRACTION', op: '>=' },
      { value: 40, regime: 'CRISIS', op: '>=' },
    ],
    crossed_cuts: [{ value: 20, regime: 'LATE_BULL', op: '>' }],
    nearest_cut_distance: { cut: 25, regime: 'TRANSITION', op: '>=', distance: 2.6 },
    ...over,
  }
}

function mkPayload(components: RegimeComponent[]): RegimeDetail {
  return { available: true, regime: 'LATE_BULL', components }
}

describe('MP2-TREND S3 — RegimeComponents (E1/E2/E3/E4/E6)', () => {
  it('E1: 7칸 그리드 렌더 + 현재값/거리 라벨', () => {
    const comps = ['vix', 'move', 'hy_oas_pct', 'nfci', 't10y2y_pct', 't10y3m_pct', 'drawdown_pct'].map(
      // 미통과(crossed_cuts=[]) → 거리 라벨 노출 경로.
      (k) => mkComponent({ key: k, crossed_cuts: [] }),
    )
    render(<RegimeComponents payload={mkPayload(comps)} />)
    expect(screen.getByTestId('regime-components')).toBeInTheDocument()
    // 7칸 전부
    for (const k of ['vix', 'move', 'hy_oas_pct', 'nfci', 't10y2y_pct', 't10y3m_pct', 'drawdown_pct']) {
      expect(screen.getByTestId(`comp-cell-${k}`)).toBeInTheDocument()
    }
    // 거리 라벨(전환 컷 25까지 +2.6)
    expect(screen.getByTestId('dist-vix')).toHaveTextContent('전환 컷(25)까지 +2.6')
  })

  it('E2: 컷 hlines가 payload cuts 그대로 렌더(하드코딩 없음 — payload 변경 시 추종)', () => {
    // payload를 변형(컷 2개만) → 렌더 컷도 2개(추종 증명)
    const custom = mkComponent({
      key: 'vix',
      cuts: [
        { value: 15, regime: 'TRANSITION', op: '>=' },
        { value: 99, regime: 'CRISIS', op: '>=' },
      ],
    })
    render(<RegimeComponents payload={mkPayload([custom])} />)
    expect(screen.getByTestId('cut-vix-15')).toBeInTheDocument()
    expect(screen.getByTestId('cut-vix-99')).toBeInTheDocument()
    // 원래 25/30/40 컷은 payload에 없으니 미렌더(하드코딩 아님 증명)
    expect(screen.queryByTestId('cut-vix-25')).not.toBeInTheDocument()
  })

  it('E3: crossed_cuts 있으면 "⚠ 컷 통과" 표시', () => {
    const crossed = mkComponent({
      key: 'vix',
      crossed_cuts: [{ value: 20, regime: 'LATE_BULL', op: '>' }],
      nearest_cut_distance: { cut: 25, regime: 'TRANSITION', op: '>=', distance: 2.6 },
    })
    render(<RegimeComponents payload={mkPayload([crossed])} />)
    expect(screen.getByTestId('dist-vix')).toHaveTextContent('⚠ 컷 통과')
  })

  it('E4: 세그먼트 컨트롤 — 기본=판정거리, z 탭 → placeholder', () => {
    render(<RegimeComponents payload={mkPayload([mkComponent({})])} />)
    // 기본 탭 = 판정 거리(그리드 노출)
    expect(screen.getByTestId('tab-raw')).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByTestId('comp-cell-vix')).toBeInTheDocument()
    expect(screen.queryByTestId('zscore-placeholder')).not.toBeInTheDocument()
    // z 탭 클릭 → placeholder 전환, 그리드 숨김
    fireEvent.click(screen.getByTestId('tab-z'))
    expect(screen.getByTestId('zscore-placeholder')).toBeInTheDocument()
    expect(screen.queryByTestId('comp-cell-vix')).not.toBeInTheDocument()
  })

  it('E6: 히스테리시스 캡션 존재', () => {
    render(<RegimeComponents payload={mkPayload([mkComponent({})])} />)
    expect(screen.getByTestId('hysteresis-caption')).toHaveTextContent('2일 유지 시 확정')
  })

  it('빈 components → 미렌더(graceful)', () => {
    const { container } = render(<RegimeComponents payload={{ available: true, components: [] }} />)
    expect(container.querySelector('[data-testid="regime-components"]')).toBeNull()
  })
})

describe('MP2-TREND S3 — hlines 오버레이 (E5 회귀 + 병존)', () => {
  const series: TrendSeries[] = [
    { key: 'a', label: 'A', points: DATES.map((d, i) => ({ date: d, value: i })) },
  ]

  it('E5: hlines 미전달 시 기존 소비처와 동일 출력(무영향) — 리드아웃/범례 정상', () => {
    const { rerender } = render(<MultiLineTrendChart series={series} emphasis={{ default: ['a'] }} />)
    const before = screen.getByTestId('trend-readout').textContent
    // hlines 추가해도 리드아웃/토글 등 기존 DOM 불변(hlines는 SVG 오버레이, 외부 DOM 무영향)
    rerender(
      <MultiLineTrendChart
        series={series}
        emphasis={{ default: ['a'] }}
        overlays={{ hlines: [{ value: 2, label: '컷' }] }}
      />,
    )
    expect(screen.getByTestId('trend-readout').textContent).toBe(before)
    expect(screen.getByTestId('trend-range-7')).toBeInTheDocument()
  })

  it('E4(병존): vlines + hlines 동시 전달 시 오류 없이 렌더', () => {
    expect(() =>
      render(
        <MultiLineTrendChart
          series={series}
          overlays={{ vlines: [{ date: DATES[2], label: '전환' }], hlines: [{ value: 2 }] }}
        />,
      ),
    ).not.toThrow()
  })
})
