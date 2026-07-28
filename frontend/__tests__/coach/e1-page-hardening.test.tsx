/**
 * P3-A — E1 화면 통합 검증 보강 (a11y + 폼 검증).
 *
 * Part 2의 빈/happy/error 3 케이스는 그대로 유지. 보강은:
 *   1. a11y 단언 — loading 시 aria-busy, error 시 role=alert.
 *   2. 폼 검증 — portfolio_id를 비우면 제출 버튼 disabled (mutation 미트리거).
 *
 * 화면·데이터 레이어 무수정 (검증만 보강).
 */

import { API_BASE_URL } from '@/lib/api/config'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE1ServerError, mockE1Success } from '../mocks/handlers'
import { E1CoachContent } from '@/app/coach/e1/page'

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

describe('E1 coach page — a11y + 폼 검증 보강', () => {
  it('a11y: 로딩 시 결과 영역 aria-busy=true, 완료 후 false', async () => {
    const user = userEvent.setup()
    // 지연 응답 핸들러 — 로딩 상태를 관측 가능하게 만든다
    let resolveResponse!: () => void
    const responseDone = new Promise<void>((res) => {
      resolveResponse = res
    })
    server.use(
      mockE1Success(),
      // 위 핸들러를 다시 한 번 wrap해 강제 지연
    )
    // mockE1Success는 즉시 응답하므로 isPending을 잡기 어려움.
    // 대신 직접 핸들러 등록 — http.post 사용.
    const { http, HttpResponse } = await import('msw')
    const API_URL = API_BASE_URL
    server.use(
      http.post(`${API_URL}/coach/e1/`, async () => {
        await responseDone
        return HttpResponse.json(
          { output: { summary: 's', confidence: 'high', metrics_table: '' }, llm_metadata: {} },
          { status: 200 },
        )
      }),
    )

    wrap(<E1CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    // 로딩 상태 진입 — aria-busy=true
    await waitFor(() => expect(screen.getByTestId('loading-state')).toBeInTheDocument())
    const liveRegion = screen.getByTestId('loading-state').parentElement
    expect(liveRegion).toHaveAttribute('aria-busy', 'true')

    // 응답 해제 → 완료
    resolveResponse()
    await waitFor(() => expect(screen.getByTestId('commentary-card')).toBeInTheDocument())
    expect(liveRegion).toHaveAttribute('aria-busy', 'false')
  })

  it('a11y: 에러 시 role=alert (스크린리더가 즉시 읽음)', async () => {
    const user = userEvent.setup()
    server.use(mockE1ServerError())

    wrap(<E1CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(() => expect(screen.getByTestId('error-state')).toBeInTheDocument())
    const errorBox = screen.getByTestId('error-state')
    expect(errorBox).toHaveAttribute('role', 'alert')
  })

  it('폼 검증: portfolio_id 비우면 제출 버튼 disabled (mutation 미트리거)', async () => {
    const user = userEvent.setup()
    // 핸들러를 등록하지 않음 — 만약 요청이 나가면 onUnhandledRequest:'error'로 테스트 실패
    wrap(<E1CoachContent />)

    const portfolioInput = screen.getByLabelText(/포트폴리오 ID/) as HTMLInputElement
    await user.clear(portfolioInput)

    const submitBtn = screen.getByRole('button', { name: /진단 실행/ })
    expect(submitBtn).toBeDisabled()

    // 시도로 클릭해도 mutation은 트리거되지 않아야 함
    await user.click(submitBtn)
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument()
    expect(screen.queryByTestId('commentary-card')).not.toBeInTheDocument()
  })

  it('폼 검증: 모든 종목 행을 비우면 제출 버튼 disabled', async () => {
    const user = userEvent.setup()
    wrap(<E1CoachContent />)

    // 두 행의 ticker를 모두 비우면 validRows 0 → 버튼 disabled
    const tickerInputs = screen.getAllByLabelText(/ticker$/)
    for (const input of tickerInputs) {
      await user.clear(input)
    }

    const submitBtn = screen.getByRole('button', { name: /진단 실행/ })
    expect(submitBtn).toBeDisabled()
  })
})
