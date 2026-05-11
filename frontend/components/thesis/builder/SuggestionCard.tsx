'use client'

import { Check } from 'lucide-react'
import type { ThesisSuggestion } from '@/lib/thesis/types'

interface SuggestionCardProps {
  suggestion: ThesisSuggestion
  onSelect: () => void
  isLoading?: boolean
  variant?: 'active' | 'selected' | 'dimmed'
}

export function SuggestionCard({
  suggestion, onSelect, isLoading, variant = 'active',
}: SuggestionCardProps) {
  const isBullish = suggestion.direction === 'bullish'
  const directionIcon = isBullish ? '↑' : '↓'
  const directionLabel = isBullish ? '상승' : '하락'

  const isHistory = variant !== 'active'
  const isDimmed = variant === 'dimmed'
  const isSelected = variant === 'selected'

  // 색상 — variant에 따라 분기
  const borderColor = isDimmed
    ? 'border-gray-800'
    : isBullish ? 'border-emerald-700/50' : 'border-red-700/50'
  const hoverBorder = isHistory ? '' : (isBullish ? 'hover:border-emerald-500/70' : 'hover:border-red-500/70')
  const directionBg = isDimmed
    ? 'bg-gray-800 text-gray-500'
    : isBullish ? 'bg-emerald-900/30 text-emerald-400' : 'bg-red-900/30 text-red-400'
  const ctaBg = isBullish
    ? 'bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700'
    : 'bg-red-600 hover:bg-red-500 active:bg-red-700'
  const premiseDot = isDimmed ? 'text-gray-700' : (isBullish ? 'text-emerald-600' : 'text-red-600')

  return (
    <div
      className={`flex flex-col ${isHistory ? 'p-3' : 'p-4'} bg-gray-900 border ${borderColor} ${hoverBorder}
                  rounded-xl transition-all ${isDimmed ? 'opacity-35' : ''}`}
    >
      {/* 방향 뱃지 + 선택 상태 */}
      <div className="flex items-center justify-between">
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md
                      text-xs font-medium ${directionBg}`}
        >
          {directionIcon} {directionLabel}
        </span>
        {isSelected && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md
                          text-[10px] font-medium bg-blue-900/40 text-blue-400">
            <Check size={10} /> 선택됨
          </span>
        )}
      </div>

      {/* 제목 */}
      <h3 className={`${isHistory ? 'text-xs' : 'text-sm'} font-semibold mt-2 leading-snug
                       ${isDimmed ? 'text-gray-500' : 'text-white'}`}>
        {suggestion.title}
      </h3>

      {/* 핵심 논리 — 히스토리에서는 축소 */}
      <p className={`${isHistory ? 'text-[11px] line-clamp-2' : 'text-[13px]'} mt-1 leading-relaxed
                     ${isDimmed ? 'text-gray-600' : 'text-gray-300'}`}>
        {suggestion.summary}
      </p>

      {/* 전제 목록 — 히스토리에서는 제목만 */}
      {suggestion.premises.length > 0 && (
        <div className={`${isHistory ? 'mt-2 pt-2' : 'mt-3 pt-3'} border-t border-gray-800
                         ${isHistory ? 'space-y-1' : 'space-y-2.5'}`}>
          {!isHistory && (
            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">근거</p>
          )}
          {suggestion.premises.map((p, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className={`${premiseDot} ${isHistory ? 'mt-0.5 text-xs' : 'mt-1 text-sm'} flex-shrink-0 leading-none`}>•</span>
              <div className="min-w-0">
                <p className={`${isHistory ? 'text-[11px]' : 'text-xs'} font-medium leading-snug
                               ${isDimmed ? 'text-gray-600' : 'text-gray-200'}`}>
                  {p.title}
                </p>
                {!isHistory && p.description && (
                  <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">
                    {p.description}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CTA 버튼 — active 모드에서만 */}
      {!isHistory && (
        <button
          onClick={onSelect}
          disabled={isLoading}
          className={`mt-4 w-full py-2.5 text-white text-sm font-medium rounded-lg
                      ${ctaBg} active:scale-[0.98] transition-all
                      disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {isLoading ? '처리 중...' : '이 가설로 시작 →'}
        </button>
      )}
    </div>
  )
}
