/**
 * ConfidenceBadge — Slice 17 Step 0 신규. 안 B 핵심 원자 컴포넌트.
 *
 * CommentaryCard(카드형) / E4MessageBubble(말풍선) 양쪽에 동일 의미의 배지가
 * 중복되어 있던 것을 본 컴포넌트로 통합. 외형 컨테이너(card/bubble wrapper)는
 * 절대 흡수하지 않는다 — 배지(원자 요소) 자체만.
 *
 * - props: { confidence, size? }
 * - size variant — 'md'(기본, 카드용) / 'sm'(말풍선용). 시각 회귀 0 보장을 위해
 *   Part 1에서 도입. 두 표현 정체성 차이(카드 = 강조, 말풍선 = 내포)에 맞춤.
 * - 라벨/배경은 `lib/coach/styles.ts:CONFIDENCE_STYLE` 단일 소스 소비
 * - 부모가 위치/정렬을 결정 (본 컴포넌트는 inline 형태만 보장)
 */

'use client'

import { CheckCircle2 } from 'lucide-react'

import { CONFIDENCE_STYLE } from '@/lib/coach/styles'
import type { CommentaryConfidence } from '@/lib/coach/types'

type BadgeSize = 'sm' | 'md'

interface ConfidenceBadgeProps {
  confidence: CommentaryConfidence
  size?: BadgeSize
}

const SIZE_STYLE: Record<BadgeSize, { badge: string; icon: string }> = {
  md: { badge: 'gap-1 px-3 py-1 text-xs', icon: 'h-3.5 w-3.5' },
  sm: { badge: 'gap-1 px-2 py-0.5 text-[11px]', icon: 'h-3 w-3' },
}

export default function ConfidenceBadge({ confidence, size = 'md' }: ConfidenceBadgeProps) {
  const meta = CONFIDENCE_STYLE[confidence]
  const sizeMeta = SIZE_STYLE[size]
  return (
    <span
      data-testid="confidence-badge"
      className={`inline-flex items-center rounded-full border font-medium ${sizeMeta.badge} ${meta.cls}`}
    >
      <CheckCircle2 className={sizeMeta.icon} />
      신뢰도 {meta.label}
    </span>
  )
}
