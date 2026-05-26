/**
 * Slice 16 Part 5 — useE4Coach 데이터 레이어 테스트.
 *
 * E5 패턴 복제 + E4 특수 (대화형: conversation_history 누적, user_question 신규만).
 * 3건 (첫 질문 happy / 멀티턴 payload 단언 / error).
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE4ServerError, mockE4Success } from '../mocks/handlers'
import { useE4Coach } from '@/lib/coach/hooks'
import {
  sampleE4InputEmptyHistory,
  sampleE4InputTwoTurnHistory,
} from '@/lib/coach/fixtures/e4'
import type { E4Response } from '@/lib/coach/types'

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
const E4_URL = `${API_URL}/coach/e4/`

describe('useE4Coach', () => {
  it('첫 질문 happy-path: 200 → 봉투 { output, llm_metadata } 정합', async () => {
    server.use(
      mockE4Success({
        output: {
          summary: 'HHI 0.40, 중간 수준 집중도입니다.',
          confidence: 'medium',
          key_observations: ['HHI 0.40', 'Tech 65%'],
        },
      }),
    )

    const { result } = renderHook(() => useE4Coach(), { wrapper: createWrapper() })
    result.current.mutate(sampleE4InputEmptyHistory)

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })

    const data: E4Response | undefined = result.current.data
    expect(data).toBeDefined()
    expect(data!.output.summary).toBe('HHI 0.40, 중간 수준 집중도입니다.')
    expect(data!.output.confidence).toBe('medium')
    expect(data!.output.key_observations).toHaveLength(2)
    // E4Output에는 action_items/risk_flags/quoted_metrics/metrics_table 부재 — base only.
    expect(data!.output).not.toHaveProperty('action_items')
    expect(data!.output).not.toHaveProperty('risk_flags')
    expect(data!.llm_metadata).toBeDefined()
  })

  it('멀티턴: 누적 conversation_history + 신규 user_question payload 단언', async () => {
    let capturedBody: unknown = null
    server.use(
      http.post(E4_URL, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(
          {
            output: { summary: 'AAPL 비중 축소 검토 권장', confidence: 'medium' },
            llm_metadata: {},
          },
          { status: 200 },
        )
      }),
    )

    const { result } = renderHook(() => useE4Coach(), { wrapper: createWrapper() })
    result.current.mutate(sampleE4InputTwoTurnHistory)

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 3000 })

    // E4Turn 계약: conversation_history는 이전 2 turn, user_question은 신규만.
    expect(capturedBody).toMatchObject({
      user_question: 'Tech 비중을 줄이려면 어떤 종목부터 검토하면 좋을까요?',
      conversation_history: [
        { role: 'user', content: expect.any(String) },
        { role: 'assistant', content: expect.any(String) },
      ],
    })
    // 신규 질문이 history에 섞이지 않음을 보강 — 마지막 turn은 assistant.
    const body = capturedBody as { conversation_history: { role: string }[] }
    expect(body.conversation_history.at(-1)?.role).toBe('assistant')
  })

  it('error-path: 500 → error 노출 + data undefined', async () => {
    server.use(mockE4ServerError())

    const { result } = renderHook(() => useE4Coach(), { wrapper: createWrapper() })
    result.current.mutate(sampleE4InputEmptyHistory)

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 })

    expect(result.current.error?.response?.status).toBe(500)
    expect(result.current.data).toBeUndefined()
  })
})
