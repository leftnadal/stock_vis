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
  const premiseDot = isBullish ? 'text-emerald-600' : 'text-red-600'

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

      {/* 제목 */}
      <h3 className="text-sm text-white font-semibold mt-2.5 leading-snug">
        {suggestion.title}
      </h3>

      {/* 핵심 논리 (summary) */}
      <p className="text-[13px] text-gray-300 mt-1.5 leading-relaxed">
        {suggestion.summary}
      </p>

      {/* 전제 목록 — 제목 + 설명 */}
      {suggestion.premises.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-800 space-y-2.5">
          <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">
            근거
          </p>
          {suggestion.premises.map((p, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className={`${premiseDot} mt-1 flex-shrink-0 text-sm leading-none`}>•</span>
              <div className="min-w-0">
                <p className="text-xs text-gray-200 font-medium leading-snug">
                  {p.title}
                </p>
                {p.description && (
                  <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">
                    {p.description}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CTA 버튼 */}
      <button
        onClick={onSelect}
        disabled={isLoading}
        className={`mt-4 w-full py-2.5 text-white text-sm font-medium rounded-lg
                    ${ctaBg} active:scale-[0.98] transition-all
                    disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {isLoading ? '처리 중...' : '이 가설로 시작 →'}
      </button>
    </div>
  )
}
