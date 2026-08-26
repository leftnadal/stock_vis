// 일지 kind=snapshot 렌더러 (MON-DETAIL-P1 T2) — 점수·Δ.
import type { JournalEntry, SnapshotPayload } from '@/lib/monitor/journal'
import { dirArrow, formatScore } from '@/utils/formatters'

export function SnapshotEntry({ entry }: { entry: JournalEntry }) {
  const p = entry.payload as SnapshotPayload
  const delta = p.delta
  const deltaTone =
    delta == null || delta === 0
      ? 'text-gray-400'
      : delta > 0
        ? 'text-green-600 dark:text-green-400'
        : 'text-red-600 dark:text-red-400'
  return (
    <div className="flex items-baseline justify-between gap-2" data-testid="journal-snapshot">
      <span className="text-sm text-gray-600 dark:text-gray-300">
        종합 점수 <span className="font-medium text-gray-900 dark:text-gray-100">{formatScore(p.score)}</span>
      </span>
      {delta != null && (
        <span className={`text-xs font-medium ${deltaTone}`}>
          {dirArrow(delta, 3) || '·'} {formatScore(delta, { signed: true })}
        </span>
      )}
    </div>
  )
}
