// Monitor 빌더 4단계 흐름 검증 (MON-P3-S2)
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const push = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }))

const invalidateQueries = vi.fn()
vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ invalidateQueries }),
}))

vi.mock('@/components/auth/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/hooks/useMonitor', () => ({
  monitorKeys: { lists: () => ['monitor', 'list'] },
  useIndicatorCatalog: () => ({
    data: [
      {
        key: 'eod_composite',
        name: 'EOD 종합 신호',
        indicator_type: 'market_data',
        default_direction: 'positive',
        source: 'stocks.EODSignal.composite_score',
        unit: '점수(-1~1)',
        description: '합성 점수',
      },
    ],
  }),
  // TIMING-P2: 빌더 4단계 가격 제안 훅 (테스트에선 미가용으로 배너 숨김)
  useScenarioSuggest: () => ({ data: { available: false } }),
}))

const create = vi.fn()
const createIndicator = vi.fn()
const createClaim = vi.fn()
vi.mock('@/services/monitorService', () => ({
  monitorService: {
    create: (...a: unknown[]) => create(...a),
    createIndicator: (...a: unknown[]) => createIndicator(...a),
    createClaim: (...a: unknown[]) => createClaim(...a),
  },
}))

import MonitorBuilderPage from '@/app/monitor/new/page'

beforeEach(() => {
  push.mockReset()
  create.mockReset()
  createIndicator.mockReset()
  createClaim.mockReset()
})

describe('MonitorBuilder 4단계', () => {
  it('종목 scope만 활성, 시장/섹터/펀드는 준비 중(disabled)', () => {
    render(<MonitorBuilderPage />)
    expect(screen.getByText('종목')).toBeEnabled()
    expect(screen.getByText('시장').closest('button')).toBeDisabled()
  })

  it('전 흐름: 대상→지표→Claim→생성 후 리스트 복귀', async () => {
    create.mockResolvedValue({ id: 'mon-1' })
    createIndicator.mockResolvedValue({})
    createClaim.mockResolvedValue({})
    render(<MonitorBuilderPage />)

    fireEvent.click(screen.getByText('다음')) // step1 stock → step2
    fireEvent.change(screen.getByPlaceholderText('심볼 (예: AAPL)'), {
      target: { value: 'aapl' },
    })
    fireEvent.change(screen.getByPlaceholderText('이 모니터의 이름'), {
      target: { value: '애플 감시' },
    })
    fireEvent.click(screen.getByText('다음')) // step2 → step3

    fireEvent.click(screen.getByText('EOD 종합 신호')) // 지표 선택
    fireEvent.click(screen.getByText('다음')) // step3 → step4

    fireEvent.change(
      screen.getByPlaceholderText('예: 실적 개선으로 3개월 내 반등한다'),
      { target: { value: '반등한다' } }
    )
    fireEvent.click(screen.getByText('만들기'))

    await waitFor(() => expect(push).toHaveBeenCalledWith('/monitor'))
    expect(invalidateQueries).toHaveBeenCalled() // 생성 후 리스트 캐시 무효화(stale 방지)
    expect(create).toHaveBeenCalledWith({
      scope: 'stock',
      target_ref: 'AAPL',
      name: '애플 감시',
    })
    expect(createIndicator).toHaveBeenCalledWith(
      expect.objectContaining({ monitor: 'mon-1', source_key: 'eod_composite' })
    )
    expect(createClaim).toHaveBeenCalledWith(
      expect.objectContaining({ monitor: 'mon-1', assertion: '반등한다' })
    )
  })

  it('심볼 검증 실패(API 400) → 대상 지정 단계로 복귀 + 에러', async () => {
    create.mockRejectedValue({
      response: { data: { target_ref: ['존재하지 않는 종목: NOPE'] } },
    })
    render(<MonitorBuilderPage />)
    fireEvent.click(screen.getByText('다음'))
    fireEvent.change(screen.getByPlaceholderText('심볼 (예: AAPL)'), {
      target: { value: 'NOPE' },
    })
    fireEvent.change(screen.getByPlaceholderText('이 모니터의 이름'), {
      target: { value: 'x' },
    })
    fireEvent.click(screen.getByText('다음')) // →3
    fireEvent.click(screen.getByText('다음')) // →4
    fireEvent.click(screen.getByText('만들기'))

    await waitFor(() =>
      expect(screen.getByText(/존재하지 않는 종목/)).toBeInTheDocument()
    )
    expect(push).not.toHaveBeenCalled()
    expect(screen.getByTestId('step-target')).toBeInTheDocument() // 2단계 복귀
  })
})
