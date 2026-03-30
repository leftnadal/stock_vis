'use client'

import type { ThesisSuggestion } from '@/lib/thesis/types'

interface SuggestionCardProps {
  suggestion: ThesisSuggestion
  onSelect: () => void
  isLoading?: boolean
}

export function SuggestionCard({ suggestion, onSelect, isLoading }: SuggestionCardProps) {
  const isBullish = suggestion.direction === 'bullish'
  const directionIcon = isBullish ? '↑' : '↓'
  const directionLabel = isBullish ? '상승' : '하락'

  const borderColor = isBullish ? 'border-emerald-700/50' : 'border-red-700/50'
  const hoverBorder = isBullish ? 'hover:border-emerald-500/70' : 'hover:border-red-500/70'
  const directionBg = isBullish ? 'bg-emerald-900/30 text-emerald-400' : 'bg-red-900/30 text-red-400'
  const ctaBg = isBullish
    ? 'bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700'
    : 'bg-red-600 hover:bg-red-500 active:bg-red-700'

  const visiblePremises = suggestion.premises.slice(0, 2)
  const hiddenCount = Math.max(0, suggestion.premises.length - 2)

  return (
    <div
      className={`flex flex-col p-4 bg-gray-900 border ${borderColor} ${hoverBorder}
                  rounded-xl transition-all`}
    >
      {/* 방향 뱃지 */}
      <span
        className={`inline-flex items-center gap-1 self-start px-2 py-0.5 rounded-md
                    text-xs font-medium ${directionBg}`}
      >
        {directionIcon} {directionLabel}
      </span>

      {/* 제목 + 요약 */}
      <h3 className="text-sm text-white font-semibold mt-2 leading-snug">
        {suggestion.title}
      </h3>
      <p className="text-xs text-gray-400 mt-1 line-clamp-2 leading-relaxed">
        {suggestion.summary}
      </p>

      {/* 전제 목록 */}
      {visiblePremises.length > 0 && (
        <ul className="mt-3 space-y-1">
          {visiblePremises.map((p, i) => (
            <li key={i} className="text-xs text-gray-400 flex items-start gap-1.5">
              <span className="text-gray-600 mt-0.5 flex-shrink-0">·</span>
              <span className="line-clamp-1">{p.title}</span>
            </li>
          ))}
          {hiddenCount > 0 && (
            <li className="text-xs text-gray-500 pl-3">
              +{hiddenCount}개 더보기
            </li>
          )}
        </ul>
      )}

      {/* CTA 버튼 */}
      <button
        onClick={onSelect}
        disabled={isLoading}
        className={`mt-3 w-full py-2.5 text-white text-sm font-medium rounded-lg
                    ${ctaBg} active:scale-[0.98] transition-all
                    disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {isLoading ? '처리 중...' : '이 가설로 시작 →'}
      </button>
    </div>
  )
}
