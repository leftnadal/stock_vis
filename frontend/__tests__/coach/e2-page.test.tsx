/**
 * Slice 16 Part 1 — E2 화면 렌더 테스트 (MSW 위에서).
 *
 * E1 화면 테스트 패턴 복제(`e1-page.test.tsx` + `e1-page-hardening.test.tsx`):
 *   기본: 빈/happy/error 3건
 *   보강: a11y(aria-busy/role=alert) + 폼 검증 2건
 *   합계 5건.
 *
 * AuthGuard 우회: E2CoachContent named export 직접 렌더.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE2ServerError, mockE2Success } from '../mocks/handlers'
import { E2CoachContent } from '@/app/coach/e2/page'

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

describe('E2 coach page (E2CoachContent)', () => {
  it('빈 상태: 제출 전 empty-state 노출, CommentaryCard 미렌더', () => {
    wrap(<E2CoachContent />)

    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.queryByTestId('commentary-card')).not.toBeInTheDocument()
    expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument()
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('happy-path: 제출 → CommentaryCard에 summary + quoted_metrics 렌더', async () => {
    const user = userEvent.setup()
    server.use(
      mockE2Success({
        output: {
          summary: '안정적 분산 — Tech/Healthcare 균형',
          confidence: 'high',
          key_observations: ['1년 수익률 12.5%', 'Tech 50% / Healthcare 50%'],
          quoted_metrics: { tech_weight: 0.5, healthcare_weight: 0.5 },
          metrics_table: '',
        },
      }),
    )

    wrap(<E2CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(
      () => expect(screen.getByTestId('commentary-card')).toBeInTheDocument(),
      { timeout: 3000 },
    )
    expect(screen.getByText('안정적 분산 — Tech/Healthcare 균형')).toBeInTheDocument()
    // quoted_metrics 섹션이 새 BarChart3 헤더 + key 라벨로 표시되는지
    expect(screen.getByText('인용 지표')).toBeInTheDocument()
    expect(screen.getByText('tech_weight')).toBeInTheDocument()
    // 빈/에러는 사라져야 함
    expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('error-path: 500 → 친화적 에러 메시지 (원시 노출 없음)', async () => {
    const user = userEvent.setup()
    server.use(mockE2ServerError())

    wrap(<E2CoachContent />)
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
    server.use(mockE2ServerError())

    wrap(<E2CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(() => expect(screen.getByTestId('error-state')).toBeInTheDocument())
    expect(screen.getByTestId('error-state')).toHaveAttribute('role', 'alert')
  })

  it('폼 검증: portfolio_id 비우면 submit 버튼 disabled', async () => {
    const user = userEvent.setup()
    wrap(<E2CoachContent />)

    const portfolioInput = screen.getByLabelText(/포트폴리오 ID/) as HTMLInputElement
    await user.clear(portfolioInput)

    const submitBtn = screen.getByRole('button', { name: /진단 실행/ })
    expect(submitBtn).toBeDisabled()

    await user.click(submitBtn)
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument()
  })
})
