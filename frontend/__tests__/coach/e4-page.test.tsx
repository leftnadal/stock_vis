/**
 * Slice 16 Part 5 — E4 화면 렌더 테스트 (MSW 위에서).
 *
 * 대화형 안 C 특수: conversation_history 누적 + user_question 신규만 전송 +
 * assistant turn content == output.summary (E4Turn 계약). CommentaryCard 미사용,
 * E4MessageBubble로 좌/우 말풍선 렌더.
 *
 * 6건:
 *   1. empty + 빈 history 첫 질문 payload 단언
 *   2. 멀티턴 — 2번째 제출 시 payload.conversation_history에 2 turn 누적
 *   3. assistant 응답 → summary + observations 불릿 + confidence 배지 렌더
 *   4. user_question 빈/공백 → 전송 버튼 disabled
 *   5. MSW error → role=alert + 입력칸 유지
 *   6. assistant turn content == output.summary (E4Turn 계약 종단 검증)
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { server } from '../mocks/server'
import { mockE4ServerError, mockE4Success } from '../mocks/handlers'
import { E4CoachContent } from '@/app/coach/e4/page'

function wrap(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
const E4_URL = `${API_URL}/coach/e4/`

describe('E4 coach page (E4CoachContent)', () => {
  it('빈 thread + 첫 질문 제출 → payload.conversation_history === []', async () => {
    const user = userEvent.setup()
    let capturedBody: unknown = null
    server.use(
      http.post(E4_URL, async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(
          {
            output: { summary: '첫 답변', confidence: 'medium' },
            llm_metadata: {},
          },
          { status: 200 },
        )
      }),
    )

    wrap(<E4CoachContent />)
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()

    await user.type(screen.getByLabelText('질문 텍스트'), '첫 질문입니다')
    await user.click(screen.getByRole('button', { name: /전송/ }))

    // 응답 수신 후 assistant 말풍선이 등장 — empty-state 사라짐.
    await waitFor(() => expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument())
    expect(capturedBody).toMatchObject({
      user_question: '첫 질문입니다',
      conversation_history: [],
    })
  })

  it('멀티턴: 2번째 제출 시 payload.conversation_history에 1턴 user+assistant 누적', async () => {
    const user = userEvent.setup()
    const captured: unknown[] = []
    server.use(
      http.post(E4_URL, async ({ request }) => {
        const body = await request.json()
        captured.push(body)
        // 첫 호출은 짧은 답, 두번째도 짧은 답 (멀티턴 누적이 핵심).
        const summary = captured.length === 1 ? '1턴 답변 summary' : '2턴 답변 summary'
        return HttpResponse.json(
          { output: { summary, confidence: 'medium' }, llm_metadata: {} },
          { status: 200 },
        )
      }),
    )

    wrap(<E4CoachContent />)

    // 1턴
    await user.type(screen.getByLabelText('질문 텍스트'), '첫 질문')
    await user.click(screen.getByRole('button', { name: /전송/ }))
    await waitFor(() => expect(screen.getByText('1턴 답변 summary')).toBeInTheDocument())

    // 2턴
    await user.type(screen.getByLabelText('질문 텍스트'), '후속 질문')
    await user.click(screen.getByRole('button', { name: /전송/ }))
    await waitFor(() => expect(screen.getByText('2턴 답변 summary')).toBeInTheDocument())

    // 두 호출 모두 capture됨, 두번째 payload의 conversation_history에 2 turn.
    expect(captured).toHaveLength(2)
    expect(captured[0]).toMatchObject({
      user_question: '첫 질문',
      conversation_history: [],
    })
    expect(captured[1]).toMatchObject({
      user_question: '후속 질문',
      conversation_history: [
        { role: 'user', content: '첫 질문' },
        { role: 'assistant', content: '1턴 답변 summary' },
      ],
    })
  })

  it('assistant 응답 → summary + observations 불릿 + confidence 배지 렌더', async () => {
    const user = userEvent.setup()
    server.use(
      mockE4Success({
        output: {
          summary: 'HHI 0.40, 중간 수준 집중도',
          confidence: 'high',
          key_observations: ['HHI 0.40 — 중간 수준', 'Tech 65% — 단일 섹터 노출'],
        },
      }),
    )

    wrap(<E4CoachContent />)
    await user.type(screen.getByLabelText('질문 텍스트'), '집중도 어떤가요')
    await user.click(screen.getByRole('button', { name: /전송/ }))

    const bubble = await screen.findByTestId('e4-bubble-assistant')
    expect(within(bubble).getByText('HHI 0.40, 중간 수준 집중도')).toBeInTheDocument()
    expect(within(bubble).getByText(/HHI 0.40 — 중간 수준/)).toBeInTheDocument()
    expect(within(bubble).getByText(/Tech 65%/)).toBeInTheDocument()
    expect(within(bubble).getByText(/신뢰도 높음/)).toBeInTheDocument()
  })

  it('user_question 빈/공백 → 전송 버튼 disabled', async () => {
    const user = userEvent.setup()
    wrap(<E4CoachContent />)

    const sendBtn = screen.getByRole('button', { name: /전송/ })
    // 초기 — 빈 상태
    expect(sendBtn).toBeDisabled()

    // 공백만 — 여전히 disabled
    await user.type(screen.getByLabelText('질문 텍스트'), '   ')
    expect(sendBtn).toBeDisabled()

    // 실제 텍스트 — 활성화
    await user.type(screen.getByLabelText('질문 텍스트'), '실 질문')
    expect(sendBtn).not.toBeDisabled()
  })

  it('MSW error → role=alert + 입력칸 유지', async () => {
    const user = userEvent.setup()
    server.use(mockE4ServerError())

    wrap(<E4CoachContent />)
    const textarea = screen.getByLabelText('질문 텍스트') as HTMLTextAreaElement
    await user.type(textarea, '에러 유발 질문')
    await user.click(screen.getByRole('button', { name: /전송/ }))

    await waitFor(() => expect(screen.getByTestId('error-state')).toBeInTheDocument())
    expect(screen.getByTestId('error-state')).toHaveAttribute('role', 'alert')
    expect(screen.getByText(/답변 생성에 실패/)).toBeInTheDocument()

    // 입력칸은 비우지 않음 — 사용자가 재시도 가능.
    expect(textarea.value).toBe('에러 유발 질문')
    // 메시지 thread는 변경 없음 (empty-state 유지).
    expect(screen.getByTestId('empty-state')).toBeInTheDocument()
  })

  it('E4Turn 계약: assistant turn content === output.summary (key_observations 미포함)', async () => {
    const user = userEvent.setup()
    const captured: unknown[] = []
    server.use(
      http.post(E4_URL, async ({ request }) => {
        const body = await request.json()
        captured.push(body)
        return HttpResponse.json(
          {
            output: {
              summary: 'SUMMARY-ONLY-CONTENT',
              confidence: 'medium',
              key_observations: ['Obs1', 'Obs2'],
            },
            llm_metadata: {},
          },
          { status: 200 },
        )
      }),
    )

    wrap(<E4CoachContent />)
    await user.type(screen.getByLabelText('질문 텍스트'), 'Q1')
    await user.click(screen.getByRole('button', { name: /전송/ }))
    await waitFor(() => expect(screen.getByText('SUMMARY-ONLY-CONTENT')).toBeInTheDocument())

    // 2턴 트리거 — 이때 conversation_history에 assistant turn이 들어가는데,
    // 그 content가 summary만이고 observations 텍스트는 섞이지 않았는지 확인.
    await user.type(screen.getByLabelText('질문 텍스트'), 'Q2')
    await user.click(screen.getByRole('button', { name: /전송/ }))
    await waitFor(() => expect(captured).toHaveLength(2))

    const secondBody = captured[1] as {
      conversation_history: { role: string; content: string }[]
    }
    const assistantTurn = secondBody.conversation_history.find((t) => t.role === 'assistant')
    expect(assistantTurn?.content).toBe('SUMMARY-ONLY-CONTENT')
    // observations 텍스트가 content에 섞이지 않음.
    expect(assistantTurn?.content).not.toMatch(/Obs1|Obs2/)
  })
})
