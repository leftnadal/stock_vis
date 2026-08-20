// 출처 3색 배지(수동/규칙/통계) — 근거 입력·대결 화면 공용 단일 컴포넌트(RECON-SWAP-0813, 불변 요소).
import { SOURCE_TONE_META, type SourceTone } from '@/lib/monitor/evidence'

interface SourceBadgeProps {
  tone: SourceTone
  className?: string
}

export function SourceBadge({ tone, className }: SourceBadgeProps) {
  const meta = SOURCE_TONE_META[tone]
  return (
    <span
      data-testid="source-badge"
      data-tone={tone}
      className={`inline-flex flex-shrink-0 items-center rounded px-1.5 py-0.5 text-[10px] font-medium ${meta.cls} ${className ?? ''}`}
    >
      {meta.label}
    </span>
  )
}
