/**
 * Slice 16 Part 2 — E6 화면 렌더 테스트 (MSW 위에서).
 *
 * E1/E2 화면 테스트 패턴 복제. 5건:
 *   기본: 빈/happy/error 3건
 *   보강: a11y(role=alert) + 폼 검증 2건
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE6ServerError, mockE6Success } from '../mocks/handlers'
import { E6CoachContent } from '@/app/coach/e6/page'

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

describe('E6 coach page (E6CoachContent)', () => {
  it('빈 상태: 제출 전 empty-state 노출, CommentaryCard 미렌더', () => {
    wrap(<E6CoachContent />)

    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.queryByTestId('commentary-card')).not.toBeInTheDocument()
    expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument()
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('happy-path: 제출 → summary + risk_flags + quoted_metrics 렌더', async () => {
    const user = userEvent.setup()
    server.use(
      mockE6Success({
        output: {
          summary: 'AAPL 우위 / NVDA 차익실현',
          confidence: 'high',
          key_observations: ['AAPL score 0.78', 'NVDA score 0.42'],
          risk_flags: ['NVDA 변동성 ↑'],
          quoted_metrics: { avg_score: 0.6, bull_signals: 1 },
        },
      }),
    )

    wrap(<E6CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(
      () => expect(screen.getByTestId('commentary-card')).toBeInTheDocument(),
      { timeout: 3000 },
    )
    expect(screen.getByText('AAPL 우위 / NVDA 차익실현')).toBeInTheDocument()
    // risk_flags 섹션 렌더 (E1 패턴 — '리스크' 헤더)
    expect(screen.getByText('리스크')).toBeInTheDocument()
    expect(screen.getByText('NVDA 변동성 ↑')).toBeInTheDocument()
    // quoted_metrics 섹션 (Part 1 일반화 — '인용 지표' 헤더)
    expect(screen.getByText('인용 지표')).toBeInTheDocument()
    expect(screen.getByText('avg_score')).toBeInTheDocument()
    expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('error-path: 500 → 친화적 에러 메시지 (원시 노출 없음)', async () => {
    const user = userEvent.setup()
    server.use(mockE6ServerError())

    wrap(<E6CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(
      () => expect(screen.getByTestId('error-state')).toBeInTheDocument(),
      { timeout: 3000 },
    )
    expect(screen.getByText(/진단 생성에 실패했습니다/)).toBeInTheDocument()
    expect(screen.queryByTestId('commentary-card')).not.toBeInTheDocument()
    expect(screen.queryByText(/500/)).not.toBeInTheDocument()
    expect(screen.queryByText(/AxiosError/)).not.toBeInTheDocument()
  })

  it('a11y: 에러 시 error-state에 role="alert"', async () => {
    const user = userEvent.setup()
    server.use(mockE6ServerError())

    wrap(<E6CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(() => expect(screen.getByTestId('error-state')).toBeInTheDocument())
    expect(screen.getByTestId('error-state')).toHaveAttribute('role', 'alert')
  })

  it('폼 검증: portfolio_id 비우면 submit 버튼 disabled', async () => {
    const user = userEvent.setup()
    wrap(<E6CoachContent />)

    const portfolioInput = screen.getByLabelText(/포트폴리오 ID/) as HTMLInputElement
    await user.clear(portfolioInput)

    const submitBtn = screen.getByRole('button', { name: /진단 실행/ })
    expect(submitBtn).toBeDisabled()

    await user.click(submitBtn)
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument()
  })
})
