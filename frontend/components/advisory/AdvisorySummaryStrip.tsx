// 요약 스트립 (Slice 20a §4) — 총자산 · 진행 갭 · 배치 갭 · 모드 뱃지 · 기준일.
import { formatKRW, formatPercent } from '@/utils/formatters'
import type { AdvisoryMode, AssetSummary } from '@/types/advisory'

const MODE_META: Record<AdvisoryMode, { label: string; chip: string }> = {
  BUY: {
    label: 'BUY 모드',
    chip: 'bg-green-50 text-green-700 border-green-300 dark:bg-green-900/25 dark:text-green-300 dark:border-green-700',
  },
  DEFEND: {
    label: 'DEFEND 모드',
    chip: 'bg-blue-50 text-blue-700 border-blue-300 dark:bg-blue-900/25 dark:text-blue-300 dark:border-blue-700',
  },
}

function toNumber(v: unknown): number | null {
  if (typeof v === 'number') return v
  if (typeof v === 'string') {
    const n = Number(v)
    return isNaN(n) ? null : n
  }
  return null
}

interface AdvisorySummaryStripProps {
  summary: AssetSummary
}

export function AdvisorySummaryStrip({ summary }: AdvisorySummaryStripProps) {
  const gapPct = toNumber((summary.progress_gap as Record<string, unknown> | undefined)?.gap_pct)
  const idleRatio = toNumber(
    (summary.allocation_gap as Record<string, unknown> | undefined)?.idle_ratio
  )
  const mode = summary.mode
  const asOf = summary.date ?? summary.price_as_of

  return (
    <div
      data-testid="advisory-summary-strip"
      className="grid grid-cols-2 gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900 sm:grid-cols-5"
    >
      <div className="flex flex-col">
        <span className="text-[11px] text-gray-400">총자산</span>
        <span data-testid="summary-total-krw" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {summary.total_krw != null ? formatKRW(summary.total_krw) : '—'}
        </span>
      </div>
      <div className="flex flex-col">
        <span className="text-[11px] text-gray-400">진행 갭</span>
        <span data-testid="summary-progress-gap" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {gapPct != null ? formatPercent(gapPct) : '—'}
        </span>
      </div>
      <div className="flex flex-col">
        <span className="text-[11px] text-gray-400">배치 갭(유휴현금)</span>
        <span data-testid="summary-allocation-gap" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {idleRatio != null ? formatPercent(idleRatio * 100) : '—'}
        </span>
      </div>
      <div className="flex flex-col">
        <span className="text-[11px] text-gray-400">모드</span>
        {mode ? (
          <span
            data-testid="summary-mode-badge"
            className={`mt-0.5 inline-flex w-fit items-center rounded-full border px-2 py-0.5 text-xs font-medium ${MODE_META[mode].chip}`}
          >
            {MODE_META[mode].label}
          </span>
        ) : (
          <span className="text-lg text-gray-400">—</span>
        )}
      </div>
      <div className="flex flex-col">
        <span className="text-[11px] text-gray-400">기준일</span>
        <span data-testid="summary-as-of" className="text-sm text-gray-600 dark:text-gray-400">
          {asOf ?? '—'}
        </span>
      </div>
    </div>
  )
}
