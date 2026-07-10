/**
 * MP2-TREND S4 — z-이상도 뷰(예약 탭 → 실 뷰) 회귀.
 *
 * 커버리지: 정렬(|z| 내림차순·null·insufficient 최후미) / danger 칩(|z|≥2) /
 *   고정 캡션 / placeholder 제거 / RegimeZSparkline(null 단절·음영·danger 도트).
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RegimeComponents } from '@/app/market-pulse-v2/details/RegimeComponents'
import { RegimeZSparkline } from '@/app/market-pulse-v2/details/RegimeZSparkline'
import type {
  RegimeComponent,
  RegimeDetail,
  RegimeZComponent,
} from '@/lib/api/marketPulseV2'

// useRegimeZScore mock — z 데이터 주입(QueryClient 불요).
const mockUseZ = vi.fn()
vi.mock('@/hooks/useMarketPulseV2', () => ({
  useRegimeZScore: (enabled: boolean) => mockUseZ(enabled),
}))

function mkRaw(): RegimeComponent {
  return {
    key: 'vix',
    unit: '',
    current: 22,
    series: [{ date: '2026-07-01', value: 22 }],
    cuts: [],
    crossed_cuts: [],
    nearest_cut_distance: null,
  }
}
const rawPayload: RegimeDetail = { available: true, components: [mkRaw()] }

function zComp(key: string, zs: (number | null)[], insufficient = false): RegimeZComponent {
  return {
    key,
    unit: '',
    series: zs.map((z, i) => ({ date: `2026-07-0${i + 1}`, z })),
    baseline: { mean: 0, std: 1, n: 703 },
    insufficient,
  }
}

function zResult(components: RegimeZComponent[], lowConf = '2023-08-04') {
  return {
    data: { data: { available: true, components, meta: { low_confidence_until: lowConf } } },
    isLoading: false,
    isError: false,
  }
}

beforeEach(() => mockUseZ.mockReset())

describe('S4 z 뷰', () => {
  it('z 탭 → placeholder 제거 + 캡션 + 그리드', () => {
    mockUseZ.mockReturnValue(zResult([zComp('vix', [0.5, 1.0])]))
    render(<RegimeComponents payload={rawPayload} />)
    fireEvent.click(screen.getByTestId('tab-z'))
    expect(screen.queryByTestId('zscore-placeholder')).not.toBeInTheDocument()
    expect(screen.getByTestId('zview')).toBeInTheDocument()
    expect(screen.getByTestId('zview-caption')).toHaveTextContent('±2σ')
    expect(screen.getByTestId('zview-caption')).toHaveTextContent('저신뢰 초입')
  })

  it('정렬: |현재 z| 내림차순, null·insufficient 최후미', () => {
    const comps = [
      zComp('vix', [0.1, 0.2]), // |z|=0.2
      zComp('move', [1.0, 3.5]), // |z|=3.5 → 최상단
      zComp('nfci', [null, null]), // 현재 z null → null군
      zComp('hy_oas_pct', [0.0, -1.5]), // |z|=1.5
      zComp('drawdown_pct', [], true), // insufficient → 최후미
    ]
    mockUseZ.mockReturnValue(zResult(comps))
    render(<RegimeComponents payload={rawPayload} />)
    fireEvent.click(screen.getByTestId('tab-z'))
    const cells = screen.getAllByTestId(/^zcomp-cell-/)
    const order = cells.map((c) => c.getAttribute('data-testid'))
    expect(order).toEqual([
      'zcomp-cell-move', // 3.5
      'zcomp-cell-hy_oas_pct', // 1.5
      'zcomp-cell-vix', // 0.2
      'zcomp-cell-nfci', // null
      'zcomp-cell-drawdown_pct', // insufficient 최후미
    ])
  })

  it('danger 칩: |z|≥2 → rose, 그 외 중립', () => {
    mockUseZ.mockReturnValue(zResult([zComp('vix', [0, 2.4]), zComp('move', [0, 0.8])]))
    render(<RegimeComponents payload={rawPayload} />)
    fireEvent.click(screen.getByTestId('tab-z'))
    expect(screen.getByTestId('zchip-vix').className).toContain('rose')
    expect(screen.getByTestId('zchip-move').className).not.toContain('rose')
  })

  it('insufficient 성분 → 기준 부족 칩 + 스파크라인 미렌더', () => {
    mockUseZ.mockReturnValue(zResult([zComp('vix', [], true)]))
    render(<RegimeComponents payload={rawPayload} />)
    fireEvent.click(screen.getByTestId('tab-z'))
    expect(screen.getByTestId('zchip-vix')).toHaveTextContent('기준 부족')
    expect(screen.queryByTestId('zspark-vix')).not.toBeInTheDocument()
  })

  it('로딩 상태', () => {
    mockUseZ.mockReturnValue({ data: undefined, isLoading: true, isError: false })
    render(<RegimeComponents payload={rawPayload} />)
    fireEvent.click(screen.getByTestId('tab-z'))
    expect(screen.getByTestId('zview-loading')).toBeInTheDocument()
  })
})

describe('RegimeZSparkline', () => {
  it('null → 선 단절(세그먼트 2개)', () => {
    const c = zComp('vix', [0.5, 1.0, null, -0.5, -1.0])
    const { container } = render(<RegimeZSparkline component={c} />)
    expect(container.querySelectorAll('polyline').length).toBe(2)
  })

  it('lowConfidenceUntil → 좌측 음영 rect', () => {
    const c = zComp('vix', [0.5, 1.0, 0.2])
    const { getByTestId } = render(
      <RegimeZSparkline component={c} lowConfidenceUntil="2026-07-03" />,
    )
    const rect = getByTestId('zspark-shade-vix')
    expect(Number(rect.getAttribute('width'))).toBeGreaterThan(0)
  })

  it('|z|≥2 최신점 → danger 도트 색', () => {
    const c = zComp('vix', [0, 2.5])
    const { container } = render(<RegimeZSparkline component={c} />)
    const dot = container.querySelector('circle')
    expect(dot?.getAttribute('fill')).toBe('#e11d48')
  })

  it('present 0 → 기준 불충분 문구', () => {
    const c = zComp('vix', [null, null])
    render(<RegimeZSparkline component={c} />)
    expect(screen.getByText('기준 불충분')).toBeInTheDocument()
  })
})
