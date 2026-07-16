/**
 * Slice 16 Part 4 — E5 화면 렌더 테스트 (MSW 위에서).
 *
 * 기본 3건(빈/happy/error) + a11y/form + E5 안 C 특수 검증 4건
 * (extraction_targets 빈 차단 / 토글 off=null / 토글 on + current 미입력 차단 /
 *  예시 채우기 버튼). 총 8건.
 */

import { API_BASE_URL } from '@/lib/api/config'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE5ServerError, mockE5Success } from '../mocks/handlers'
import { E5CoachContent } from '@/app/coach/e5/page'

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const API_URL = API_BASE_URL
const E5_URL = `${API_URL}/coach/e5/`

describe('E5 coach page (E5CoachContent)', () => {
  it('빈 상태: 제출 전 empty-state 노출', () => {
    wrap(<E5CoachContent />)
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    expect(screen.queryByTestId('commentary-card')).not.toBeInTheDocument()
  })

  it('happy-path: 제출 → summary + action_items + quoted_metrics 렌더', async () => {
    const user = userEvent.setup()
    server.use(
      mockE5Success({
        output: {
          summary: '배당수익률 3.45% 우상향',
          confidence: 'high',
          action_items: [
            {
              title: '배당 성장 모니터링',
              description: '4분기 변화율 추적',
              priority: 'medium',
              category: 'monitor',
            },
          ],
          quoted_metrics: { dividend_yield: '3.45%', beta: '1.12' },
        },
      }),
    )

    wrap(<E5CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(
      () => expect(screen.getByTestId('commentary-card')).toBeInTheDocument(),
      { timeout: 3000 },
    )
    expect(screen.getByText('배당수익률 3.45% 우상향')).toBeInTheDocument()
    expect(screen.getByText('추천 액션')).toBeInTheDocument()
    expect(screen.getByText('배당 성장 모니터링')).toBeInTheDocument()
    expect(screen.getByText('인용 지표')).toBeInTheDocument()
    expect(screen.getByText('dividend_yield')).toBeInTheDocument()
  })

  it('error-path: 500 → role=alert + 친화 문구 (원시 노출 없음)', async () => {
    const user = userEvent.setup()
    server.use(mockE5ServerError())

    wrap(<E5CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(() => expect(screen.getByTestId('error-state')).toBeInTheDocument())
    expect(screen.getByTestId('error-state')).toHaveAttribute('role', 'alert')
    expect(screen.getByText(/진단 생성에 실패했습니다/)).toBeInTheDocument()
    expect(screen.queryByText(/500/)).not.toBeInTheDocument()
    expect(screen.queryByText(/AxiosError/)).not.toBeInTheDocument()
  })

  it('폼 검증: extraction_targets 비우면 submit disabled', async () => {
    const user = userEvent.setup()
    wrap(<E5CoachContent />)

    const targetsInput = screen.getByLabelText(/추출 대상/) as HTMLInputElement
    await user.clear(targetsInput)

    const submitBtn = screen.getByRole('button', { name: /진단 실행/ })
    expect(submitBtn).toBeDisabled()
    expect(screen.getByText(/현재 0개 키 입력됨/)).toBeInTheDocument()
  })

  it('time_series_context 토글 off (default) → payload에 null 전달', async () => {
    const user = userEvent.setup()
    let capturedBody: unknown = null
    server.use(
      http.post(E5_URL, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(
          {
            output: { summary: 'ok', confidence: 'high' },
            llm_metadata: {},
          },
          { status: 200 },
        )
      }),
    )

    wrap(<E5CoachContent />)
    // 토글은 default off — 그대로 제출
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(() => expect(screen.getByTestId('commentary-card')).toBeInTheDocument())
    expect(capturedBody).toMatchObject({ time_series_context: null })
  })

  it('time_series_context 토글 on + current 미입력 → submit disabled + role=alert 에러', async () => {
    const user = userEvent.setup()
    wrap(<E5CoachContent />)

    // 토글 on (current 비어있는 상태)
    await user.click(screen.getByLabelText(/시계열 컨텍스트 포함/))

    const submitBtn = screen.getByRole('button', { name: /진단 실행/ })
    expect(submitBtn).toBeDisabled()
    // 에러 메시지 role=alert
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent(/current.*값을 입력/)
  })

  it('"예시 값 채우기" → 4칸이 fixture 상수로 채워지고 제출 가능 + payload string 직렬화', async () => {
    const user = userEvent.setup()
    let capturedBody: unknown = null
    server.use(
      http.post(E5_URL, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(
          { output: { summary: 'ok', confidence: 'high' }, llm_metadata: {} },
          { status: 200 },
        )
      }),
    )

    wrap(<E5CoachContent />)
    await user.click(screen.getByLabelText(/시계열 컨텍스트 포함/))
    await user.click(screen.getByRole('button', { name: /예시 값 채우기/ }))

    // 4칸이 fixture 상수로 채워짐
    expect((screen.getByLabelText(/시계열 current/) as HTMLInputElement).value).toBe('3.45')
    expect((screen.getByLabelText(/시계열 window_1q/) as HTMLInputElement).value).toBe('3.40')
    expect((screen.getByLabelText(/시계열 window_4q/) as HTMLInputElement).value).toBe('3.30')
    expect((screen.getByLabelText(/시계열 window_12q/) as HTMLInputElement).value).toBe('3.15')

    // 오인 방지 텍스트
    expect(screen.getByText(/실제 값으로 교체/)).toBeInTheDocument()

    // 제출 → payload의 time_series_context가 string 직렬화 형태로 전달
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))
    await waitFor(() => expect(screen.getByTestId('commentary-card')).toBeInTheDocument())

    expect(capturedBody).toMatchObject({
      time_series_context: {
        current: '3.45',
        window_1q: '3.40',
        window_4q: '3.30',
        window_12q: '3.15',
      },
    })
  })

  it('a11y: 로딩 시 결과 영역 aria-busy=true → 응답 후 false', async () => {
    const user = userEvent.setup()
    let resolveResponse!: () => void
    const responseDone = new Promise<void>((res) => {
      resolveResponse = res
    })
    server.use(
      http.post(E5_URL, async () => {
        await responseDone
        return HttpResponse.json(
          { output: { summary: 's', confidence: 'high' }, llm_metadata: {} },
          { status: 200 },
        )
      }),
    )

    wrap(<E5CoachContent />)
    await user.click(screen.getByRole('button', { name: /진단 실행/ }))

    await waitFor(() => expect(screen.getByTestId('loading-state')).toBeInTheDocument())
    const liveRegion = screen.getByTestId('loading-state').parentElement
    expect(liveRegion).toHaveAttribute('aria-busy', 'true')

    resolveResponse()
    await waitFor(() => expect(screen.getByTestId('commentary-card')).toBeInTheDocument())
    expect(liveRegion).toHaveAttribute('aria-busy', 'false')
  })
})
