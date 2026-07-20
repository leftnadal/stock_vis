// TIMING-P2 빌더 매수 시나리오 — 가격 검증(stop<entry<target·미래 기한) + 제안 적용.
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

const suggestData = { available: true, symbol: 'AAPL', entry_suggest: 98, stop_suggest: 92, basis: '제안 근거' }
vi.mock('@/hooks/useMonitor', () => ({
  monitorKeys: { lists: () => ['monitor', 'list'] },
  useIndicatorCatalog: () => ({ data: [] }),
  useScenarioSuggest: () => ({ data: suggestData }),
}))

const create = vi.fn()
const createIndicator = vi.fn()
const createClaim = vi.fn()
vi.mock('@/services/monitorService', () => ({
  monitorService: {
    create: (...a: unknown[]) => create(...a),
    createIndicator: (...a: unknown[]) => createIndicator(...a),
    createClaim: (...a: unknown[]) => createClaim(...a),
    scenarioSuggest: async () => ({ available: false }), // 정합 힌트 미가용
  },
}))

import MonitorBuilderPage from '@/app/monitor/new/page'

const FUTURE = '2099-01-01'

function gotoStep4() {
  render(<MonitorBuilderPage />)
  fireEvent.click(screen.getByText('다음')) // 1→2
  fireEvent.change(screen.getByPlaceholderText('심볼 (예: AAPL)'), { target: { value: 'aapl' } })
  fireEvent.change(screen.getByPlaceholderText('이 모니터의 이름'), { target: { value: '애플' } })
  fireEvent.click(screen.getByText('다음')) // 2→3
  fireEvent.click(screen.getByText('다음')) // 3→4
}

beforeEach(() => {
  push.mockReset()
  create.mockReset()
  createIndicator.mockReset()
  createClaim.mockReset()
  create.mockResolvedValue({ id: 'mon-1' })
  createClaim.mockResolvedValue({})
})

describe('빌더 매수 시나리오 검증', () => {
  it('잘못된 가격 순서 → 에러 표시 + 제출 차단', () => {
    gotoStep4()
    fireEvent.change(screen.getByTestId('scenario-entry-price'), { target: { value: '100' } })
    fireEvent.change(screen.getByTestId('scenario-target-price'), { target: { value: '90' } }) // target<entry
    fireEvent.change(screen.getByTestId('scenario-stop-price'), { target: { value: '80' } })
    fireEvent.change(screen.getByTestId('scenario-deadline'), { target: { value: FUTURE } })
    expect(screen.getByTestId('scenario-error')).toHaveTextContent('손절가 < 진입가 < 목표가')
    expect(screen.getByText('만들기')).toBeDisabled()
  })

  it('과거 기한 → 에러', () => {
    gotoStep4()
    fireEvent.change(screen.getByTestId('scenario-entry-price'), { target: { value: '100' } })
    fireEvent.change(screen.getByTestId('scenario-target-price'), { target: { value: '120' } })
    fireEvent.change(screen.getByTestId('scenario-stop-price'), { target: { value: '90' } })
    fireEvent.change(screen.getByTestId('scenario-deadline'), { target: { value: '2000-01-01' } })
    expect(screen.getByTestId('scenario-error')).toHaveTextContent('미래 날짜')
  })

  it('유효 시나리오 → 제출 + createClaim 가격 포함', async () => {
    gotoStep4()
    fireEvent.change(screen.getByTestId('scenario-entry-price'), { target: { value: '100' } })
    fireEvent.change(screen.getByTestId('scenario-target-price'), { target: { value: '120' } })
    fireEvent.change(screen.getByTestId('scenario-stop-price'), { target: { value: '90' } })
    fireEvent.change(screen.getByTestId('scenario-deadline'), { target: { value: FUTURE } })
    expect(screen.queryByTestId('scenario-error')).toBeNull()
    fireEvent.click(screen.getByText('만들기'))
    await waitFor(() => expect(push).toHaveBeenCalledWith('/monitor'))
    expect(createClaim).toHaveBeenCalledWith(
      expect.objectContaining({
        monitor: 'mon-1',
        entry_price: '100',
        target_price: '120',
        stop_price: '90',
        deadline: FUTURE,
      })
    )
  })

  it('메모 없는 시나리오 → assertion 가격으로 자동 합성(BE non-blank 방어)', async () => {
    gotoStep4()
    fireEvent.change(screen.getByTestId('scenario-entry-price'), { target: { value: '349.2' } })
    fireEvent.change(screen.getByTestId('scenario-target-price'), { target: { value: '400' } })
    fireEvent.change(screen.getByTestId('scenario-stop-price'), { target: { value: '324.94' } })
    fireEvent.change(screen.getByTestId('scenario-deadline'), { target: { value: FUTURE } })
    fireEvent.click(screen.getByText('만들기'))
    await waitFor(() => expect(createClaim).toHaveBeenCalled())
    const arg = createClaim.mock.calls[0][0]
    expect(arg.assertion).toContain('진입 349.2')
    expect(arg.assertion).not.toBe('') // non-blank 보장
  })

  it('제안 배너 [적용] → 진입/손절 입력 채움', () => {
    gotoStep4()
    expect(screen.getByTestId('scenario-suggest-banner')).toHaveTextContent('제안 근거')
    fireEvent.click(screen.getByTestId('scenario-suggest-apply'))
    expect(screen.getByTestId('scenario-entry-price')).toHaveValue(98)
    expect(screen.getByTestId('scenario-stop-price')).toHaveValue(92)
  })
})
