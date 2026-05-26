/**
 * E4MessageBubble — Slice 16 Part 5. E4 전용 경량 대화 말풍선.
 *
 * 안 C 확정 (Part 5 §0): CommentaryCard 미사용 — 대화 UX에는 카드가 무겁다.
 * 단 데이터 계약(CommentaryCardData base)은 정합 유지하기 위해 assistant 메시지의
 * summary / key_observations / confidence 3 필드만 graceful 렌더.
 *
 * - user 말풍선: 우측 정렬, 입력한 질문 1줄 텍스트
 * - assistant 말풍선: 좌측 정렬, summary(메인 답변) + observations 불릿(있을 때만)
 *   + confidence 배지(있을 때만). action_items / risk_flags / quoted_metrics는
 *   E4Output 스키마에 없으므로 본 컴포넌트도 받지 않는다.
 */

'use client'

import { CheckCircle2 } from 'lucide-react'

import type { CommentaryConfidence } from '@/lib/coach/types'

interface E4MessageBubbleProps {
  role: 'user' | 'assistant'
  content: string
  observations?: string[]
  confidence?: CommentaryConfidence
}

const CONFIDENCE_STYLE: Record<CommentaryConfidence, { label: string; cls: string }> = {
  high: { label: '높음', cls: 'bg-green-100 text-green-800 border-green-300' },
  medium: { label: '보통', cls: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  low: { label: '낮음', cls: 'bg-red-100 text-red-800 border-red-300' },
}

export default function E4MessageBubble({
  role,
  content,
  observations,
  confidence,
}: E4MessageBubbleProps) {
  const isUser = role === 'user'
  const obsList = observations ?? []
  const confidenceMeta = confidence ? CONFIDENCE_STYLE[confidence] : null

  return (
    <div
      data-testid={isUser ? 'e4-bubble-user' : 'e4-bubble-assistant'}
      className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-sm ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'border border-slate-200 bg-white text-slate-900'
        }`}
      >
        {!isUser && confidenceMeta && (
          <div className="mb-2 flex items-center justify-end">
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${confidenceMeta.cls}`}
            >
              <CheckCircle2 className="h-3 w-3" />
              신뢰도 {confidenceMeta.label}
            </span>
          </div>
        )}
        <p className={`whitespace-pre-wrap text-sm ${isUser ? 'text-white' : 'text-slate-900'}`}>
          {content}
        </p>
        {!isUser && obsList.length > 0 && (
          <ul className="mt-3 list-inside list-disc space-y-1 border-t border-slate-100 pt-2 text-xs text-slate-600">
            {obsList.map((obs, idx) => (
              <li key={idx}>{obs}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
