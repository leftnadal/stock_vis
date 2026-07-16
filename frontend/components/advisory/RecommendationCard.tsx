// 권유 카드 (Slice 20a) — action/symbol/currency/lane/score/rationale 렌더.
// score는 BUY만 존재하며 "배치 우선순위 점수"(기대수익 아님)로 명시 표기한다(§2 절대 규칙).
import { ActionBadge } from '@/components/advisory/ActionBadge'
import type { Recommendation } from '@/types/advisory'

interface RecommendationCardProps {
  recommendation: Recommendation
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const { action, symbol, currency, lane, score, rationale } = recommendation
  const scoreNum = score != null ? Number(score) : null
  const scoreLabel = scoreNum != null && !isNaN(scoreNum) ? scoreNum.toFixed(2) : score

  return (
    <div
      data-testid="recommendation-card"
      data-symbol={symbol}
      className="flex flex-col gap-2 rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900"
    >
      <div className="flex items-center gap-2">
        <ActionBadge action={action} />
        <span className="font-semibold text-gray-900 dark:text-gray-100">{symbol}</span>
        <span className="text-xs text-gray-400">{currency}</span>
        {lane === 'exploration' && (
          <span
            data-testid="lane-badge"
            className="rounded-full bg-purple-50 px-2 py-0.5 text-[11px] font-medium text-purple-700 dark:bg-purple-900/25 dark:text-purple-300"
          >
            탐험
          </span>
        )}
      </div>

      {score != null && (
        <p data-testid="recommendation-score" className="text-xs text-gray-500 dark:text-gray-400">
          배치 우선순위 {scoreLabel} <span className="text-gray-400">(기대수익 아님)</span>
        </p>
      )}

      <p className="text-sm text-gray-700 dark:text-gray-300">{rationale}</p>
    </div>
  )
}
