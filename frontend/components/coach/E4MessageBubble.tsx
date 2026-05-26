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
 *
 * Slice 17 Part 1: confidence 배지를 <ConfidenceBadge size="sm" />로 치환.
 * 말풍선 wrapper / 정렬 div / summary / observations 렌더는 모두 보존 (시각
 * 회귀 0). 안 B 경계 규칙대로 BaseCard는 import하지 않는다.
 */

'use client'

import ConfidenceBadge from './ConfidenceBadge'
import type { CommentaryConfidence } from '@/lib/coach/types'

interface E4MessageBubbleProps {
  role: 'user' | 'assistant'
  content: string
  observations?: string[]
  confidence?: CommentaryConfidence
}

export default function E4MessageBubble({
  role,
  content,
  observations,
  confidence,
}: E4MessageBubbleProps) {
  const isUser = role === 'user'
  const obsList = observations ?? []

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
        {!isUser && confidence && (
          <div className="mb-2 flex items-center justify-end">
            <ConfidenceBadge confidence={confidence} size="sm" />
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
