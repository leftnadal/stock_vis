/**
 * P2-D — E1 코치 화면 렌더 테스트 (MSW 위에서).
 *
 * 검증 케이스:
 *   1. 빈 상태 — 제출 전 결과 영역에 안내 문구.
 *   2. happy-path — 폼 입력 → 제출 → CommentaryCard가 summary/action_items 렌더.
 *   3. error-path — 500 응답 → 친화적 에러 메시지 표시.
 *
 * AuthGuard는 AuthContext에 의존해 테스트가 무거워지므로 `E1CoachContent`를
 * 직접 렌더한다 (page.tsx에서 named export 노출).
 */

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

describe('E1 coach page (E1CoachContent)', () => {
  it('빈 상태: 제출 전 안내 문구 + CommentaryCard 미렌더', () => {
    wrap(<E1CoachContent />)

    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.queryByTestId('commentary-card')).not.toBeInTheDocument()
    expect(screen.queryByTestId('loading-state')).not.toBeInTheDocument()
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('happy-path: 제출 → CommentaryCard에 summary/action_items 렌더', async () => {
    const user = userEvent.setup()
    server.use(
      mockE1Success({
        output: {
          summary: '집중도 양호, 성장률 견조',
          confidence: 'high',
          key_observations: ['EPS 평균 13.5%', 'PEG 1.45'],
          action_items: [
            {
              title: 'NVDA 추가 검토',
              description: '동일 섹터 분산 효과 기대.',
              priority: 'medium',
              category: 'research',
            },
          ],
          risk_flags: ['Tech 비중 100%'],
          metrics_table: '',
        },
      }),
    )

    wrap(<E1CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(
      () => expect(screen.getByTestId('commentary-card')).toBeInTheDocument(),
      { timeout: 3000 },
    )
    expect(screen.getByText('집중도 양호, 성장률 견조')).toBeInTheDocument()
    expect(screen.getByText('NVDA 추가 검토')).toBeInTheDocument()
    expect(screen.getByText('Tech 비중 100%')).toBeInTheDocument()
    // 빈 상태 / 로딩 / 에러는 사라져야 함
    expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument()
    expect(screen.queryByTestId('error-state')).not.toBeInTheDocument()
  })

  it('error-path: 500 → 친화적 에러 메시지 (원시 에러 미노출)', async () => {
    const user = userEvent.setup()
    server.use(mockE1ServerError())

    wrap(<E1CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(
      () => expect(screen.getByTestId('error-state')).toBeInTheDocument(),
      { timeout: 3000 },
    )
    expect(screen.getByText(/진단 생성에 실패했습니다/)).toBeInTheDocument()
    expect(screen.queryByTestId('commentary-card')).not.toBeInTheDocument()
    // 원시 에러 객체나 status code를 화면에 노출하지 않는지 확인
    expect(screen.queryByText(/500/)).not.toBeInTheDocument()
    expect(screen.queryByText(/AxiosError/)).not.toBeInTheDocument()
  })
})
