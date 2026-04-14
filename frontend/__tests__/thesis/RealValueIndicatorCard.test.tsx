import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { RealValueIndicatorCard } from '@/components/thesis/dashboard/RealValueIndicatorCard'
import type { DashboardIndicator } from '@/lib/thesis/types'

// QuarterlySparkline은 캔버스 의존 없으므로 그대로 사용

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

function makeIndicator(overrides: Partial<DashboardIndicator> = {}): DashboardIndicator {
  return {
    id: 'ind-1',
    name: '원/달러 환율',
    arrow_degree: 110.5,
    score: -0.3,
    color: '#FB923C',
    label: '약화하는 편',
    previous_degree: 105.0,
    trend: 'weakening',
    premise_name: '글로벌 달러 강세',
    is_extreme_vol: false,
    raw_value: 1380,
    raw_value_unit: '원',
    previous_raw_value: 1365,
    change_pct: 1.1,
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

describe('RealValueIndicatorCard', () => {
  it('지표명, 포맷된 값, 변동률을 렌더링한다', () => {
    render(<RealValueIndicatorCard indicator={makeIndicator()} />)

    expect(screen.getByText('원/달러 환율')).toBeInTheDocument()
    // formatRawValue(1380, '원') → '1,380원'
    expect(screen.getByText('1,380원')).toBeInTheDocument()
    // formatChangePct(1.1) → '+1.1%'
    expect(screen.getByText('+1.1%')).toBeInTheDocument()
    // supportLabel(-0.3) → '반박'
    expect(screen.getByText('반박')).toBeInTheDocument()
  })

  it('raw_value가 null이면 "--"을 표시한다', () => {
    render(
      <RealValueIndicatorCard indicator={makeIndicator({ raw_value: null })} />,
    )

    // formatRawValue(null, '원') → '--'
    const dashes = screen.getAllByText('--')
    expect(dashes.length).toBeGreaterThanOrEqual(1)
  })

  it('change_pct가 null이면 변동률 자리에 "--"을 표시한다', () => {
    render(
      <RealValueIndicatorCard indicator={makeIndicator({ change_pct: null })} />,
    )

    // formatChangePct(null) → { text: '--' }
    const dashes = screen.getAllByText('--')
    expect(dashes.length).toBeGreaterThanOrEqual(1)
  })

  it('분기 지표이면 QoQ/YoY 접두사를 표시한다', () => {
    render(
      <RealValueIndicatorCard
        indicator={makeIndicator({
          is_quarterly: true,
          comparison_type: 'yoy',
          fiscal_label: '2025 Q3',
          change_pct: -5.2,
        })}
      />,
    )

    // 'YoY ' prefix + '-5.2%'
    expect(screen.getByText(/YoY/)).toBeInTheDocument()
    expect(screen.getByText(/-5\.2%/)).toBeInTheDocument()
    expect(screen.getByText('2025 Q3')).toBeInTheDocument()
  })

  it('description과 recommendation_reason이 있으면 표시한다', () => {
    render(
      <RealValueIndicatorCard
        indicator={makeIndicator({
          description: '한국 원화 대비 미국 달러 환율',
          recommendation_reason: '수출 기업 실적에 직접 영향',
        })}
      />,
    )

    expect(screen.getByText('한국 원화 대비 미국 달러 환율')).toBeInTheDocument()
    expect(screen.getByText('수출 기업 실적에 직접 영향')).toBeInTheDocument()
  })
})
