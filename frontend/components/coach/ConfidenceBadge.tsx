/**
 * ConfidenceBadge — Slice 17 Step 0 신규. 안 B 핵심 원자 컴포넌트.
 *
 * CommentaryCard(카드형) / E4MessageBubble(말풍선) 양쪽에 동일 배지 마크업이
 * 중복되어 있던 것을 본 컴포넌트로 통합. 외형 컨테이너(card/bubble wrapper)는
 * 절대 흡수하지 않는다 — 배지(원자 요소) 자체만.
 *
 * - props 최소: { confidence }
 * - 라벨/배경은 `lib/coach/styles.ts:CONFIDENCE_STYLE` 단일 소스 소비
 * - 부모가 위치/정렬을 결정 (본 컴포넌트는 inline 형태만 보장)
 */

'use client'

import { CheckCircle2 } from 'lucide-react'

import { CONFIDENCE_STYLE } from '@/lib/coach/styles'
import type { CommentaryConfidence } from '@/lib/coach/types'

interface ConfidenceBadgeProps {
  confidence: CommentaryConfidence
}

export default function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const meta = CONFIDENCE_STYLE[confidence]
  return (
    <span
      data-testid="confidence-badge"
      className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium ${meta.cls}`}
    >
      <CheckCircle2 className="h-3.5 w-3.5" />
      신뢰도 {meta.label}
    </span>
  )
}
