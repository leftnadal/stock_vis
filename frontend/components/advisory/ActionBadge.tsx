// 권유 action 배지 (Slice 20a) — BUY 초록 / HOLD 회색 / TRIM 주황.
// VerdictBadge(monitor)와 동일 로컬 정의 패턴: GRADE_CHIP(gray/orange)은 재사용,
// green은 방향축(colorSemantics) 소관 밖이라 이 컴포넌트 로컬 정의(단일 소비처).
import { GRADE_CHIP } from '@/components/common/colorSemantics'
import type { RecommendationAction } from '@/types/advisory'

const GREEN_CHIP =
  'bg-green-50 text-green-700 border-green-300 dark:bg-green-900/25 dark:text-green-300 dark:border-green-700'

const ACTION_META: Record<RecommendationAction, { label: string; chip: string }> = {
  BUY: { label: 'BUY', chip: GREEN_CHIP },
  HOLD: { label: 'HOLD', chip: GRADE_CHIP.gray },
  TRIM: { label: 'TRIM', chip: GRADE_CHIP.orange },
}

interface ActionBadgeProps {
  action: RecommendationAction
  className?: string
}

export function ActionBadge({ action, className }: ActionBadgeProps) {
  const meta = ACTION_META[action]
  return (
    <span
      data-testid="action-badge"
      data-action={action}
      className={`inline-flex flex-shrink-0 items-center rounded-full border px-2 py-1 text-xs font-medium ${meta.chip} ${className ?? ''}`}
    >
      {meta.label}
    </span>
  )
}
