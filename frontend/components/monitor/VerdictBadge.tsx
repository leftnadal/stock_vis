// 판정 배지 (MON-CLOSE-UI Phase 2 · TIMING-P2 §6) — 카드·상세·Claim 행 공용 단일 컴포넌트.
// 라벨·색은 verdictLabels 중앙 모듈 단일 소비(익절/부분 실현/손절/기한만료/불명확).
import { verdictMeta } from '@/lib/monitor/verdictLabels'
import type { Verdict } from '@/types/monitor'

interface VerdictBadgeProps {
  verdict: Verdict
  size?: 'sm' | 'md'
  className?: string
}

export function VerdictBadge({ verdict, size = 'md', className }: VerdictBadgeProps) {
  const meta = verdictMeta(verdict)
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
