/**
 * Slice 16 Part 3 — E3 화면 렌더 테스트 (MSW 위에서).
 *
 * E1/E2/E6 화면 테스트 패턴 복제. 5건.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE3ServerError, mockE3Success } from '../mocks/handlers'
import { E3CoachContent } from '@/app/coach/e3/page'

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

describe('E3 coach page (E3CoachContent)', () => {
  it('빈 상태: 제출 전 empty-state + concentration-preview는 default 행으로 렌더', () => {
    wrap(<E3CoachContent />)

    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.queryByTestId('commentary-card')).not.toBeInTheDocument()
    // 자동 도출 preview는 default rows로 렌더됨
    expect(screen.getByTestId('concentration-preview')).toBeInTheDocument()
  })

  it('happy-path: 제출 → summary + action_items + risk_flags 렌더', async () => {
    const user = userEvent.setup()
    server.use(
      mockE3Success({
        output: {
          summary: 'AAPL 60% 단일 종목 집중',
          confidence: 'high',
          key_observations: ['HHI 0.52', 'Top3 100%'],
          action_items: [
            {
              title: 'AAPL 비중 축소',
              description: '60% → 40%로 점진적 리밸런싱',
              priority: 'high',
              category: 'rebalance',
            },
          ],
          risk_flags: ['단일 종목 집중도 60%'],
        },
      }),
    )

    wrap(<E3CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(
      () => expect(screen.getByTestId('commentary-card')).toBeInTheDocument(),
      { timeout: 3000 },
    )
    expect(screen.getByText('AAPL 60% 단일 종목 집중')).toBeInTheDocument()
    // action_items 섹션 (CommentaryCard '추천 액션' 헤더)
    expect(screen.getByText('추천 액션')).toBeInTheDocument()
    expect(screen.getByText('AAPL 비중 축소')).toBeInTheDocument()
    // risk_flags 섹션
    expect(screen.getByText('리스크')).toBeInTheDocument()
    expect(screen.getByText('단일 종목 집중도 60%')).toBeInTheDocument()
    expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('error-path: 500 → 친화적 에러 메시지 (원시 노출 없음)', async () => {
    const user = userEvent.setup()
    server.use(mockE3ServerError())

    wrap(<E3CoachContent />)
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
    server.use(mockE3ServerError())

    wrap(<E3CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(() => expect(screen.getByTestId('error-state')).toBeInTheDocument())
    expect(screen.getByTestId('error-state')).toHaveAttribute('role', 'alert')
  })

  it('폼 검증: portfolio_id 비우면 submit 버튼 disabled', async () => {
    const user = userEvent.setup()
    wrap(<E3CoachContent />)

    const portfolioInput = screen.getByLabelText(/포트폴리오 ID/) as HTMLInputElement
    await user.clear(portfolioInput)

    const submitBtn = screen.getByRole('button', { name: /진단 실행/ })
    expect(submitBtn).toBeDisabled()

    await user.click(submitBtn)
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument()
  })
})
