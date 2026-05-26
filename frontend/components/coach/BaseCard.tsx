/**
 * BaseCard — Slice 17 Step 0 신규. 5 카드형 진입점(E1·E2·E3·E5·E6) 전용 골격.
 *
 * 추출 범위:
 *   1) article wrapper (rounded-2xl border bg-white p-6 shadow-sm)
 *   2) header — '진단 요약' 라벨 + summary 본문 + ConfidenceBadge
 *
 * children 슬롯에 EP별 Section들이 들어온다. CommentaryCard가 Step 0에서
 * 기존 5 섹션을 children으로 넘기는 형태로 재구성된다.
 *
 * ⚠ 안 B 경계 규칙(Slice 17 §0): E4MessageBubble은 본 컴포넌트를 import 하지
 * 않는다 — 말풍선 wrapper와 카드 wrapper는 EP 표현 정체성이 다른 컨테이너.
 */

'use client'

import type { ReactNode } from 'react'

import ConfidenceBadge from './ConfidenceBadge'
import type { CommentaryConfidence } from '@/lib/coach/types'

interface BaseCardProps {
  summary: string
  confidence: CommentaryConfidence
  children?: ReactNode
}

export default function BaseCard({ summary, confidence, children }: BaseCardProps) {
  return (
    <article
      data-testid="commentary-card"
      className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <header className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">진단 요약</p>
          <h2 className="mt-1 text-xl font-semibold text-slate-900">{summary}</h2>
        </div>
        <ConfidenceBadge confidence={confidence} />
      </header>
      {children}
    </article>
  )
}
