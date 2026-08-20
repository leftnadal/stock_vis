// D1-SCOREBOARD 3a — 성적판 요약 스트립 (오늘 채점 N · 적중 요약 · 표본 라벨).
// 자립 컴포넌트: board만 받으면 렌더(승격 이사 전제).
import type { ScorecardBoard } from '@/types/scorecard'
import { fmtPct, hitRatePct, sampleLabel } from '@/lib/scorecard/present'

interface ScoreStripProps {
  board: ScorecardBoard
}

export function ScoreStrip({ board }: ScoreStripProps) {
  const { hits, total } = board.direction_hit
  const rate = hitRatePct(hits, total)
  const isSignificant = total >= board.significance_threshold

  return (
    <div
      data-testid="score-strip"
      className="grid grid-cols-3 gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900"
    >
      <div className="flex flex-col">
        <span className="text-[11px] text-gray-400">채점 완료</span>
        <span data-testid="strip-scored-n" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {board.sample_n}건
        </span>
      </div>
      <div className="flex flex-col">
        <span className="text-[11px] text-gray-400">방향 적중</span>
        <span data-testid="strip-hit-summary" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {total > 0 ? `${hits}/${total} · ${fmtPct(rate)}` : '—'}
        </span>
      </div>
      <div className="flex flex-col">
        <span className="text-[11px] text-gray-400">표본</span>
        <span
          data-testid="strip-sample-label"
          className={`mt-0.5 inline-flex w-fit items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
            isSignificant
              ? 'border-green-300 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-900/25 dark:text-green-300'
              : 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-900/25 dark:text-amber-300'
          }`}
        >
          {sampleLabel(board)}
        </span>
      </div>
    </div>
  )
}
