// Slice 20b-f2 — 목표 생성 온보딩 (GOAL-CREATE-UI). 부재 렌더 / 생성 전환 / 실패 처리.
// AdvisoryPage.test 하네스 답습: advisoryService 직접 mock + QueryClientProvider 수동 래핑.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/components/auth/AuthGuard', () => ({
  AuthGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'jinie545' }, isAuthenticated: true, loading: false }),
}))

const getLatest = vi.fn()
const getSummary = vi.fn()
const getKnobs = vi.fn()
const createGoal = vi.fn()
const run = vi.fn()
const updateKnobs = vi.fn()

vi.mock('@/services/advisoryService', () => ({
  advisoryService: {
    getLatest: (...a: unknown[]) => getLatest(...a),
    getSummary: (...a: unknown[]) => getSummary(...a),
    getKnobs: (...a: unknown[]) => getKnobs(...a),
    createGoal: (...a: unknown[]) => createGoal(...a),
    run: (...a: unknown[]) => run(...a),
    updateKnobs: (...a: unknown[]) => updateKnobs(...a),
  },
}))

import AdvisoryPage from '@/app/advisory/page'

beforeEach(() => {
  ;[getLatest, getSummary, getKnobs, createGoal, run, updateKnobs].forEach((m) => m.mockReset())
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <AdvisoryPage />
    </QueryClientProvider>,
  )
}

// 목표 부재 기본 응답
function noGoal() {
  getLatest.mockResolvedValue({ available: false, trigger: null, run_at: null, output: null })
  getSummary.mockResolvedValue({ available: false })
  getKnobs.mockResolvedValue({ available: false })
}

describe('20b-f2 목표 생성 온보딩', () => {
  it('목표 부재 시 온보딩 카드 + create 폼(기간·성향) 렌더', async () => {
    noGoal()
    renderPage()
    await waitFor(() => expect(screen.getByTestId('goal-onboarding-card')).toBeInTheDocument())
    const form = screen.getByTestId('goal-create-form')
    expect(within(form).getByTestId('knob-target-return')).toBeInTheDocument()
    expect(within(form).getByTestId('goal-horizon')).toBeInTheDocument() // create 전용
    expect(within(form).getByTestId('goal-risk')).toBeInTheDocument() // create 전용
    expect(within(form).getByTestId('goal-create-submit')).toBeInTheDocument()
  })

  it('목표 생성 → createGoal(payload) 호출 + 성공 시 온보딩 사라짐(화면 전환)', async () => {
    const user = userEvent.setup()
    getLatest.mockResolvedValue({ available: false, trigger: null, run_at: null, output: null })
    getSummary.mockResolvedValue({ available: false })
    // 1차 부재 → 생성 후 재검증 시 목표 존재
    getKnobs
      .mockResolvedValueOnce({ available: false })
      .mockResolvedValue({ available: true, target_return_pct: '20.00', aggressiveness_offset: 0 })
    createGoal.mockResolvedValue({ available: true, target_return_pct: '20.00' })

    renderPage()
    await waitFor(() => expect(screen.getByTestId('goal-onboarding-card')).toBeInTheDocument())
    const form = screen.getByTestId('goal-create-form')

    await user.type(within(form).getByTestId('knob-target-return'), '20')
    await user.type(within(form).getByTestId('goal-horizon'), '12')
    await user.click(within(form).getByTestId('goal-create-submit'))

    await waitFor(() => expect(createGoal).toHaveBeenCalledTimes(1))
    const payload = createGoal.mock.calls[0][0]
    expect(payload.target_return_pct).toBe('20')
    expect(payload.horizon_months).toBe('12')
    expect(payload.risk_tolerance).toBe('moderate') // 기본
    expect(typeof payload.concentration_limit).toBe('string') // 손잡이 string 전송

    // 재검증 후 목표 존재 → 온보딩 카드 사라짐
    await waitFor(() =>
      expect(screen.queryByTestId('goal-onboarding-card')).not.toBeInTheDocument(),
    )
  })

  it('생성 실패(409 등) → 인라인 에러 + 온보딩 유지', async () => {
    const user = userEvent.setup()
    noGoal()
    createGoal.mockRejectedValue(new Error('409'))
    renderPage()
    await waitFor(() => expect(screen.getByTestId('goal-onboarding-card')).toBeInTheDocument())
    const form = screen.getByTestId('goal-create-form')

    await user.type(within(form).getByTestId('knob-target-return'), '20')
    await user.type(within(form).getByTestId('goal-horizon'), '12')
    await user.click(within(form).getByTestId('goal-create-submit'))

    await waitFor(() => expect(screen.getByTestId('goal-create-error')).toBeInTheDocument())
    expect(screen.getByTestId('goal-onboarding-card')).toBeInTheDocument() // 유지
  })

  it('target/horizon 미입력 제출 → createGoal 미호출 + 인라인 에러', async () => {
    const user = userEvent.setup()
    noGoal()
    renderPage()
    await waitFor(() => expect(screen.getByTestId('goal-onboarding-card')).toBeInTheDocument())
    const form = screen.getByTestId('goal-create-form')
    // 아무 것도 입력 안 하고 제출
    await user.click(within(form).getByTestId('goal-create-submit'))
    expect(within(form).getByTestId('goal-create-error')).toBeInTheDocument()
    expect(createGoal).not.toHaveBeenCalled()
  })
})
