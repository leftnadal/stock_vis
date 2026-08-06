// 일지 피드 (MON-DETAIL-P1 T2, D-MON-DETAIL-LAYOUT-B — 상세 화면의 지배 영역).
// buildJournal 결과를 kind 레지스트리로 렌더. 미등록/예약 kind는 안전 무시(전방 호환).
import type { JournalEntry } from '@/lib/monitor/journal'

import { JOURNAL_RENDERERS } from './registry'

function formatAsof(asof: string): string {
  // YYYY-MM-DD → MM/DD (간결 타임라인 라벨)
  const [, m, d] = asof.split('-')
  return m && d ? `${m}/${d}` : asof
}

export function JournalFeed({ entries }: { entries: JournalEntry[] }) {
  // 미등록 kind(예약 advisor/theme/memo 포함) 제거 → 안전 무시.
  const rendered = entries.filter((e) => JOURNAL_RENDERERS[e.kind])

  if (rendered.length === 0) {
    return (
      <p className="text-sm text-gray-400" data-testid="journal-empty">
        아직 일지 기록이 없어요.
      </p>
    )
  }

  return (
    <ol className="relative" data-testid="journal-feed">
      {rendered.map((entry, i) => {
        const Renderer = JOURNAL_RENDERERS[entry.kind]
        return (
          <li
            key={`${entry.kind}-${entry.asof}-${i}`}
            className="flex gap-3 border-b border-gray-100 py-3 last:border-0 dark:border-gray-800"
            data-testid={`journal-entry-${entry.kind}`}
          >
            <span className="w-12 flex-shrink-0 pt-0.5 text-xs tabular-nums text-gray-400">
              {formatAsof(entry.asof)}
            </span>
            <div className="min-w-0 flex-1">
              <Renderer entry={entry} />
            </div>
          </li>
        )
      })}
    </ol>
  )
}
