'use client'

import { useState } from 'react'
import { Check, ChevronDown, ChevronUp } from 'lucide-react'
import type { LLMIndicatorRecommendation } from '@/lib/thesis/types'

const SIGNAL_TYPE_LABELS: Record<string, { text: string; className: string }> = {
  leading: { text: '선행', className: 'text-blue-400 bg-blue-900/30' },
  coincident: { text: '동행', className: 'text-gray-400 bg-gray-800' },
  lagging: { text: '후행', className: 'text-amber-400 bg-amber-900/30' },
}

interface IndicatorCardProps {
  recommendation: LLMIndicatorRecommendation
  checked?: boolean
  onToggle?: () => void
}

export function IndicatorCard({ recommendation, checked = true, onToggle }: IndicatorCardProps) {
  const [expanded, setExpanded] = useState(false)
  const signalStyle = SIGNAL_TYPE_LABELS[recommendation.signal_type] ?? SIGNAL_TYPE_LABELS.coincident
  const hasDetail = !!(recommendation.why || recommendation.premise_title)

  return (
    <div
      className={`w-full rounded-xl text-left transition-all
                  ${checked
                    ? 'bg-gray-900 border border-gray-700'
                    : 'bg-gray-950 border border-gray-800 opacity-50'
                  }`}
    >
      {/* 메인 행: 체크박스 + 지표명 + 토글 */}
      <div className="flex items-center gap-3 p-3">
        {/* 체크박스 */}
        <button
          onClick={onToggle}
          className={`flex-shrink-0 w-5 h-5 rounded border flex items-center justify-center transition-colors
                      ${checked
                        ? 'bg-blue-600 border-blue-600'
                        : 'bg-transparent border-gray-600'
                      }
                      ${onToggle ? 'cursor-pointer' : ''}`}
        >
          {checked && <Check size={12} className="text-white" />}
        </button>

        {/* 지표명 + 뱃지 */}
        <div className="min-w-0 flex-1 flex items-center gap-2">
          <p className={`text-sm font-medium truncate ${checked ? 'text-white' : 'text-gray-500 line-through'}`}>
            {recommendation.indicator_name}
          </p>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0 ${signalStyle.className}`}>
            {signalStyle.text}
          </span>
        </div>

        {/* 상세 토글 버튼 */}
        {hasDetail && (
          <button
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded) }}
            className="flex-shrink-0 p-1 text-gray-500 hover:text-gray-300 transition-colors"
          >
            {expanded
              ? <ChevronUp size={16} />
              : <ChevronDown size={16} />
            }
          </button>
        )}
      </div>

      {/* 상세 영역 (토글) */}
      {expanded && hasDetail && (
        <div className={`px-3 pb-3 pt-0 ml-8 space-y-1.5 border-t border-gray-800/50 mt-0 pt-2
                         ${checked ? '' : 'opacity-60'}`}>
          {/* 추천 이유 */}
          {recommendation.why && (
            <div className="px-2.5 py-2 rounded-md bg-gray-800/60">
              <p className="text-[10px] text-gray-500 font-medium mb-0.5">추천 이유</p>
              <p className="text-[11px] text-gray-300 leading-relaxed">
                {recommendation.why}
              </p>
            </div>
          )}

          {/* 전제 연결 */}
          {recommendation.premise_title && (
            <p className="text-[10px] text-gray-500 px-1">
              연결 전제: <span className="text-gray-400">{recommendation.premise_title}</span>
            </p>
          )}
        </div>
      )}
    </div>
  )
}
