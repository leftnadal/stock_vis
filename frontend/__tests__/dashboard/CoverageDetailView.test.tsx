// CoverageDetailView 렌더 검증 (P2-COVERAGE-C1-FE, T2 + COVERAGE-DETAIL-FE)
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// impression 훅 mock — 행 단위 호출(surface·object_ref) 검증용
const useImpressionTracker = vi.fn((_surface: string, _objectRef: string) => ({
  ref: { current: null },
  onClick: vi.fn(),
}))
vi.mock('@/hooks/useImpressionTracker', () => ({
  useImpressionTracker: (surface: string, objectRef: string) =>
    useImpressionTracker(surface, objectRef),
}))

import { CoverageDetailView } from '@/components/dashboard/CoverageDetailView'
import type { CoverageResponse } from '@/types/coverage'

beforeEach(() => useImpressionTracker.mockClear())

const base: CoverageResponse = {
  window: { days: 7, from: '2026-07-20', to: '2026-07-27' },
  summary: { issued: 50, exposed: 4, exposure_rate: 0.08, unexposed_count: 46 },
  unexposed: [
    {
      object_ref: 'ACGL:2026-07-24:P5',
      ticker: 'ACGL',
      signal_date: '2026-07-24',
      signal_tag: 'P5',
      days_since_issue: 3,
    },
    {
      object_ref: 'AAPL:2026-07-24:PV1',
      ticker: 'AAPL',
      signal_date: '2026-07-24',
      signal_tag: 'PV1',
      days_since_issue: 3,
    },
  ],
  meta: { surfaces_included: ['dashboard_eod'], generated_at: 'x', join_misses: 8 },
}

describe('CoverageDetailView', () => {
  it('summary + 미노출 리스트 필드 렌더', () => {
    render(<CoverageDetailView data={base} />)
    const detail = screen.getByTestId('coverage-detail')
    expect(detail).toHaveTextContent('발급')
    expect(detail).toHaveTextContent('노출율')
    const list = screen.getByTestId('coverage-unexposed-list')
    expect(list).toHaveTextContent('ACGL')
    expect(list).toHaveTextContent('PV1')
    expect(list).toHaveTextContent('3일 경과')
  })

  it('API 응답 순서 그대로 렌더(FE 재정렬 금지)', () => {
    render(<CoverageDetailView data={base} />)
    const items = screen
      .getByTestId('coverage-unexposed-list')
      .querySelectorAll('li')
    expect(items[0]).toHaveTextContent('ACGL')
    expect(items[1]).toHaveTextContent('AAPL')
  })

  it('join_misses > 0 이면 각주 표시', () => {
    render(<CoverageDetailView data={base} />)
    expect(screen.getByTestId('coverage-join-misses')).toHaveTextContent(
      '창밖 발급 노출 8건 제외'
    )
  })

  it('join_misses = 0 이면 각주 숨김', () => {
    render(
      <CoverageDetailView data={{ ...base, meta: { ...base.meta, join_misses: 0 } }} />
    )
    expect(screen.queryByTestId('coverage-join-misses')).toBeNull()
  })

  it('미노출 0건이면 안내 문구', () => {
    render(
      <CoverageDetailView
        data={{
          ...base,
          summary: { ...base.summary, unexposed_count: 0 },
          unexposed: [],
        }}
      />
    )
    expect(screen.getByTestId('coverage-detail')).toHaveTextContent(
      '미노출 발급이 없습니다.'
    )
  })

  it('각 미노출 행이 surface=coverage_detail·object_ref로 impression 추적 연결 (COVERAGE-DETAIL-FE)', () => {
    render(<CoverageDetailView data={base} />)
    // 행 단위: unexposed 2건 각각 훅 호출
    expect(useImpressionTracker).toHaveBeenCalledTimes(2)
    expect(useImpressionTracker).toHaveBeenCalledWith('coverage_detail', 'ACGL:2026-07-24:P5')
    expect(useImpressionTracker).toHaveBeenCalledWith('coverage_detail', 'AAPL:2026-07-24:PV1')
  })

  it('미노출 0건이면 impression 훅 호출 없음(발신 0)', () => {
    render(
      <CoverageDetailView
        data={{ ...base, summary: { ...base.summary, unexposed_count: 0 }, unexposed: [] }}
      />
    )
    expect(useImpressionTracker).not.toHaveBeenCalled()
  })
})
