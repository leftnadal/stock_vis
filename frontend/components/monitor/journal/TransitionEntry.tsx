// 일지 kind=transition 렌더러 (MON-DETAIL-P1 T2) — from→to·억제 표기.
import type { JournalEntry, TransitionPayload } from '@/lib/monitor/journal'

export function TransitionEntry({ entry }: { entry: JournalEntry }) {
  const p = entry.payload as TransitionPayload
  const tone = p.is_deterioration
    ? 'text-red-600 dark:text-red-400'
    : 'text-green-600 dark:text-green-400'
  return (
    <div className="flex items-center justify-between gap-2" data-testid="journal-transition">
      <span className="text-sm">
        <span className="text-gray-400">{p.from_label}</span>
        <span className="mx-1 text-gray-400">→</span>
        <span className={`font-medium ${tone}`}>{p.to_label}</span>
      </span>
      {p.is_suppressed && (
        <span
          data-testid="journal-transition-suppressed"
          className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-500 dark:bg-gray-800 dark:text-gray-400"
        >
          쿨다운 억제
        </span>
      )}
    </div>
  )
}
