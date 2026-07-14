// 판정 배지 (MON-CLOSE-UI Phase 2) — 카드·상세·Claim 행 공용 단일 컴포넌트.
// validated=green / partial=amber / invalidated=red / inconclusive=중립 회색(표시만, 선택 불가).
import { GRADE_CHIP } from '@/components/common/colorSemantics'
import type { Verdict } from '@/types/monitor'

// colorSemantics(GRADE_CHIP)는 gray/yellow/orange/red까지만 정의 — validated(적중)의
// green은 방향축 대상이 아니라 colorSemantics 소관 밖. 여기서만 로컬 정의(단일 소비처).
const GREEN_CHIP =
  'bg-green-50 text-green-700 border-green-300 dark:bg-green-900/25 dark:text-green-300 dark:border-green-700'

const VERDICT_META: Record<Verdict, { label: string; chip: string }> = {
  validated: { label: '적중', chip: GREEN_CHIP },
  partial: { label: '부분적중', chip: GRADE_CHIP.yellow },
  invalidated: { label: '빗나감', chip: GRADE_CHIP.red },
  inconclusive: { label: '불명확', chip: GRADE_CHIP.gray },
}

interface VerdictBadgeProps {
  verdict: Verdict
  size?: 'sm' | 'md'
  className?: string
}

export function VerdictBadge({ verdict, size = 'md', className }: VerdictBadgeProps) {
  const meta = VERDICT_META[verdict] ?? VERDICT_META.inconclusive
  const sizeClass = size === 'sm' ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-1 text-xs'

  return (
    <span
      data-testid="verdict-badge"
      data-verdict={verdict}
      className={`inline-flex flex-shrink-0 items-center rounded-full border font-medium ${sizeClass} ${meta.chip} ${className ?? ''}`}
    >
      {meta.label}
    </span>
  )
}
