'use client'

/**
 * E4 대화 Q&A 페이지 — Slice 16 Part 5. 마지막 진입점.
 *
 * 안 C 확정 (Part 5 §0): CommentaryCard 미사용, 경량 메시지 말풍선
 * (E4MessageBubble) + 하단 질문 입력칸 구조. 데이터 계약은 base 정합 유지.
 *
 * 대화 상태: **화면 로컬 useState** (전역 store 금지, Part 5 §0 확정).
 * E4Turn 계약 (types.ts):
 *   - user turn content = 사용자 입력 질문 원문
 *   - assistant turn content = E4Response.output.summary (요약만)
 *
 * 전송 규칙:
 *   - 매 호출: user_question = 신규 질문만, conversation_history = 누적 turns
 *   - 응답 수신 후 user/assistant turn 2개 append, 입력칸 비움
 *
 * portfolio_id / preset / holdings는 데모 디폴트 사용 (E4의 초점은 대화 UX).
 * fetched_at은 제출 시점 ISO 문자열로 생성.
 */

import { useEffect, useRef, useState } from 'react'
import { AlertCircle, Loader2, MessagesSquare, Send } from 'lucide-react'

import { AuthGuard } from '@/components/auth/AuthGuard'
import E4MessageBubble from '@/components/coach/E4MessageBubble'
import { useE4Coach } from '@/lib/coach/hooks'
import type {
  CommentaryConfidence,
  E4Request,
  E4Turn,
} from '@/lib/coach/types'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  observations?: string[]
  confidence?: CommentaryConfidence
}

/** ChatMessage[] → E4Turn[] (서버 전송 직전 표현 정제). */
function toTurns(messages: ChatMessage[]): E4Turn[] {
  return messages.map((m) => ({ role: m.role, content: m.content }))
}

/**
 * 데모 디폴트 포트폴리오 — 대화 UX에 집중하기 위해 holdings/preset/id는 고정.
 * 추후 portfolio picker 도입 시 useState로 끌어올리면 됨.
 */
const DEMO_BASE: Pick<E4Request, 'portfolio_id' | 'preset' | 'entry_point' | 'holdings'> = {
  portfolio_id: 'demo-portfolio-e4',
  preset: 'garp',
  entry_point: 'e4',
  holdings: [
    { ticker: 'AAPL', weight: 0.4, sector: 'Tech', asset_class: 'stock', name: 'Apple' },
    { ticker: 'MSFT', weight: 0.35, sector: 'Tech', asset_class: 'stock', name: 'Microsoft' },
    {
      ticker: 'JNJ',
      weight: 0.25,
      sector: 'Healthcare',
      asset_class: 'stock',
      name: 'Johnson & Johnson',
    },
  ],
}

export function E4CoachContent() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputText, setInputText] = useState('')
  const threadRef = useRef<HTMLDivElement | null>(null)

  const mutation = useE4Coach()

  // 신규 메시지 추가 시 thread 하단 스크롤.
  useEffect(() => {
    const el = threadRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages.length, mutation.isPending])

  const trimmed = inputText.trim()
  const canSubmit = trimmed.length > 0 && !mutation.isPending

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

    const question = trimmed
    const currentTurns = toTurns(messages)

    const request: E4Request = {
      ...DEMO_BASE,
      fetched_at: new Date().toISOString(),
      user_question: question,
      conversation_history: currentTurns,
    }

    try {
      const response = await mutation.mutateAsync(request)
      // 응답 수신 → user/assistant turn 2개 append + 입력칸 비움 (Part 5 §0.2).
      const assistantTurn: ChatMessage = {
        role: 'assistant',
        content: response.output.summary, // ★ E4Turn 계약: content = summary
        observations: response.output.key_observations ?? [],
        confidence: response.output.confidence,
      }
      setMessages((cur) => [...cur, { role: 'user', content: question }, assistantTurn])
      setInputText('')
    } catch {
      // 에러는 mutation.isError로 별도 표시 — 입력칸/messages는 변경하지 않음.
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <header className="mb-6">
        <div className="mb-2 flex items-center gap-2">
          <MessagesSquare className="h-6 w-6 text-blue-600" />
          <h1 className="text-2xl font-bold text-slate-900">E4 대화 코치</h1>
        </div>
        <p className="text-sm text-slate-600">
          포트폴리오에 대해 자유롭게 질문하세요. 이전 대화 맥락을 이어가며 답변합니다.
        </p>
        <p className="mt-1 text-xs text-slate-500">
          컨텍스트: <span className="font-medium">{DEMO_BASE.portfolio_id}</span> ·{' '}
          <span className="uppercase">{DEMO_BASE.preset}</span> · 보유 {DEMO_BASE.holdings.length}
          종목
        </p>
      </header>

      <section
        ref={threadRef}
        aria-live="polite"
        aria-busy={mutation.isPending}
        className="mb-4 max-h-[60vh] min-h-[300px] space-y-3 overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 p-4"
      >
        {messages.length === 0 && !mutation.isPending && (
          <div
            data-testid="empty-state"
            className="flex h-full items-center justify-center text-sm text-slate-500"
          >
            아직 대화가 없습니다. 첫 질문을 입력해보세요.
          </div>
        )}

        {messages.map((msg, idx) => (
          <E4MessageBubble
            key={idx}
            role={msg.role}
            content={msg.content}
            observations={msg.observations}
            confidence={msg.confidence}
          />
        ))}

        {mutation.isPending && (
          <div
            data-testid="loading-state"
            className="flex items-center gap-2 text-sm text-slate-500"
          >
            <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
            AI 코치가 답변을 작성하고 있습니다...
          </div>
        )}

        {mutation.isError && (
          <div
            role="alert"
            data-testid="error-state"
            className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">답변 생성에 실패했습니다.</p>
              <p className="mt-0.5 text-red-700">
                잠시 후 다시 시도해 주세요. 입력한 질문은 그대로 유지됩니다.
              </p>
            </div>
          </div>
        )}
      </section>

      <form
        onSubmit={handleSubmit}
        className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm"
        aria-label="E4 질문 입력 폼"
      >
        <label className="flex-1 text-sm">
          <span className="sr-only">질문 입력</span>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="예) 내 포트폴리오의 집중도가 어느 정도인가요?"
            rows={2}
            maxLength={2000}
            className="w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
            aria-label="질문 텍스트"
          />
        </label>
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex h-[44px] shrink-0 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {mutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          전송
        </button>
      </form>
      <p className="mt-1 text-right text-[11px] text-slate-400">{inputText.length}/2000</p>
    </div>
  )
}

export default function E4CoachPage() {
  return (
    <AuthGuard>
      <E4CoachContent />
    </AuthGuard>
  )
}
