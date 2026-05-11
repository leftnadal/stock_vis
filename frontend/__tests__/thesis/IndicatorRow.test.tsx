import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import type { DashboardIndicator } from '@/lib/thesis/types'

// ── Mocks ──

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="chart-container">{children}</div>,
  AreaChart: ({ children }: { children: React.ReactNode }) => <div data-testid="area-chart">{children}</div>,
  Area: () => <div data-testid="area" />,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}))

vi.mock('@/lib/thesis/queries', () => ({
  useIndicatorReadings: () => ({ data: null, isLoading: false }),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/thesis/mock-1',
}))

// ── Helper: 기본 DashboardIndicator 생성 ──

function makeIndicator(overrides: Partial<DashboardIndicator> = {}): DashboardIndicator {
  return {
    id: 'ind-1',
    name: '외국인 순매수 추이',
    arrow_degree: 35.2,
    score: 0.65,
    color: '#60A5FA',
    label: '지지하는 편',
    previous_degree: 42.0,
    trend: 'strengthening',
    premise_name: 'AI 반도체 수급 개선',
    is_extreme_vol: false,
    raw_value: 1.2e12,
    raw_value_unit: '원',
    previous_raw_value: 9.8e11,
    change_pct: 22.4,
    raw_value_asof: '2026-03-18T09:00:00Z',
    fiscal_label: null,
    quarterly_history: null,
    is_quarterly: false,
    comparison_type: null,
    description: '',
    recommendation_reason: '',
    ...overrides,
  }
}

// ── 지연 import (mock 적용 후) ──
const { IndicatorRow } = await import('@/components/thesis/dashboard/IndicatorRow')

describe('IndicatorRow', () => {
  it('지표명, 포맷된 값, 지지/반박 라벨을 렌더링한다', () => {
    render(<IndicatorRow thesisId="t-1" indicator={makeIndicator()} />)

    expect(screen.getByText('외국인 순매수 추이')).toBeInTheDocument()
    // formatRawValue(1.2e12, '원') → '1.2조원'
    expect(screen.getByText('1.2조원')).toBeInTheDocument()
    // supportLabel(0.65) → '지지'
    expect(screen.getByText('지지')).toBeInTheDocument()
  })

  it('클릭 시 펼침/접힘 토글 — 펼치면 차트 영역이 나타난다', () => {
    render(<IndicatorRow thesisId="t-1" indicator={makeIndicator()} />)

    // 메인 토글 버튼 (type="button"인 첫 번째)
    const mainBtn = screen.getAllByRole('button')[0]

    // 초기 상태: 차트 영역 없음
    expect(screen.queryByText('차트 데이터 없음')).not.toBeInTheDocument()

    // 클릭 → 펼침
    fireEvent.click(mainBtn)
    // 차트 데이터가 없으므로 "차트 데이터 없음" 메시지 표시
    expect(screen.getByText('차트 데이터 없음')).toBeInTheDocument()

    // 다시 클릭 → 접힘
    fireEvent.click(mainBtn)
    expect(screen.queryByText('차트 데이터 없음')).not.toBeInTheDocument()
  })

  it('change_pct가 null이면 "--"을 표시한다', () => {
    render(
      <IndicatorRow
        thesisId="t-1"
        indicator={makeIndicator({ change_pct: null })}
      />,
    )

    expect(screen.getByText('--')).toBeInTheDocument()
  })

  it('전제(premise_name)가 있으면 표시한다', () => {
    render(
      <IndicatorRow
        thesisId="t-1"
        indicator={makeIndicator({ premise_name: 'HBM3E 양산 본격화' })}
      />,
    )

    expect(screen.getByText('HBM3E 양산 본격화')).toBeInTheDocument()
  })
})
