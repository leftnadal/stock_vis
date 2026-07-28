// CoverageStrip 상태 렌더 검증 (P2-COVERAGE-C1-FE, T1)
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const push = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }))

const useCoverageMock = vi.fn()
vi.mock('@/hooks/useCoverage', () => ({
  useCoverage: () => useCoverageMock(),
}))

import { CoverageStrip } from '@/components/dashboard/CoverageStrip'

function ok(overrides: Record<string, unknown> = {}) {
  return {
    data: {
      window: { days: 7, from: 'a', to: 'b' },
      summary: {
        issued: 50,
        exposed: 4,
        exposure_rate: 0.08,
        unexposed_count: 46,
      },
      unexposed: [],
      meta: { surfaces_included: ['dashboard_eod'], generated_at: 'x', join_misses: 0 },
      ...overrides,
    },
    isLoading: false,
    isError: false,
  }
}

beforeEach(() => {
  push.mockReset()
  useCoverageMock.mockReset()
})

describe('CoverageStrip', () => {
  it('정상: 발급/노출/율/미노출 표시', () => {
    useCoverageMock.mockReturnValue(ok())
    render(<CoverageStrip />)
    const strip = screen.getByTestId('coverage-strip')
    expect(strip).toHaveTextContent('발급')
    expect(strip).toHaveTextContent('50')
    expect(strip).toHaveTextContent('8%')
    expect(strip).toHaveTextContent('46')
  })

  it('로딩: 스켈레톤 표시', () => {
    useCoverageMock.mockReturnValue({ data: undefined, isLoading: true, isError: false })
    render(<CoverageStrip />)
    expect(screen.getByTestId('coverage-strip-skeleton')).toBeTruthy()
  })

  it('오류: fail-quiet 로 스트립 숨김(본체 무영향)', () => {
    useCoverageMock.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    const { container } = render(<CoverageStrip />)
    expect(container.firstChild).toBeNull()
  })

  it('발급 0: "이번 주 발급 없음" 문구', () => {
    useCoverageMock.mockReturnValue(
      ok({ summary: { issued: 0, exposed: 0, exposure_rate: 0, unexposed_count: 0 } })
    )
    render(<CoverageStrip />)
    expect(screen.getByTestId('coverage-strip')).toHaveTextContent('이번 주 발급 없음')
  })

  it('클릭 시 /dashboard/coverage 이동', () => {
    useCoverageMock.mockReturnValue(ok())
    render(<CoverageStrip />)
    fireEvent.click(screen.getByTestId('coverage-strip'))
    expect(push).toHaveBeenCalledWith('/dashboard/coverage')
  })
})
