/**
 * ActionItemsSection — Slice 17 Part 3 신규. Group A 첫 번째 섹션.
 *
 * 보유 EP: E1 / E3 / E5 (E5는 Part 4 조합 검증에서 확인). 본 컴포넌트는
 * CommentaryCard의 action_items 인라인 블록(L63-87, Part 2 시점 기준)을
 * 행위 보존 추출한 결과.
 *
 * - PRIORITY_STYLE 사전을 CommentaryCard에서 본 컴포넌트로 이동 — action_items
 *   단독 사용이므로 응집(Part 2의 formatQuotedMetricValue 패턴 그대로).
 * - priority 배지는 action_items 전용 원자. ConfidenceBadge와는 별개로 통합 금지
 *   (지시서 §1-1 ⚠ 명시 + 안 B 정합).
 * - 조건부 가시성은 호출처(CardSection visible)에 위임. 본 컴포넌트는 단일 책임.
 * - SectionHeader 사용 + ListChecks 아이콘 보존 (시각 회귀 0).
 */

'use client'

import { ListChecks } from 'lucide-react'

import SectionHeader from './SectionHeader'
import type {
  CommentaryActionItem,
  CommentaryActionPriority,
} from '@/lib/coach/types'

interface ActionItemsSectionProps {
  actionItems: CommentaryActionItem[]
}

const PRIORITY_STYLE: Record<CommentaryActionPriority, { label: string; cls: string }> = {
  high: { label: '즉시', cls: 'bg-red-50 text-red-700 border-red-200' },
  medium: { label: '단기', cls: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  low: { label: '장기', cls: 'bg-blue-50 text-blue-700 border-blue-200' },
}

export default function ActionItemsSection({ actionItems }: ActionItemsSectionProps) {
  return (
    <>
      <SectionHeader
        icon={<ListChecks className="h-4 w-4 text-emerald-500" />}
        title="추천 액션"
      />
      <ul className="space-y-2">
        {actionItems.map((item, idx) => {
          const priority = PRIORITY_STYLE[item.priority]
          return (
            <li key={idx} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="mb-1 flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-slate-900">{item.title}</p>
                <span
                  className={`shrink-0 rounded border px-2 py-0.5 text-[11px] font-medium ${priority.cls}`}
                >
                  {priority.label}
                </span>
              </div>
              <p className="text-sm text-slate-600">{item.description}</p>
            </li>
          )
        })}
      </ul>
    </>
  )
}
