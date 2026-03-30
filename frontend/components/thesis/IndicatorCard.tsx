'use client'

import { Check } from 'lucide-react'
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
  const signalStyle = SIGNAL_TYPE_LABELS[recommendation.signal_type] ?? SIGNAL_TYPE_LABELS.coincident

  return (
    <button
      onClick={onToggle}
      className={`w-full flex items-start gap-3 p-3 rounded-xl text-left transition-all
                  ${checked
                    ? 'bg-gray-900 border border-gray-700'
                    : 'bg-gray-950 border border-gray-800 opacity-50'
                  }
                  ${onToggle ? 'hover:border-gray-600 active:scale-[0.99] cursor-pointer' : ''}`}
    >
      {/* 체크박스 */}
      <div className={`flex-shrink-0 mt-0.5 w-5 h-5 rounded border flex items-center justify-center transition-colors
                        ${checked
                          ? 'bg-blue-600 border-blue-600'
                          : 'bg-transparent border-gray-600'
                        }`}>
        {checked && <Check size={12} className="text-white" />}
      </div>

      <div className="min-w-0 flex-1">
        {/* 지표명 + signal_type 뱃지 */}
        <div className="flex items-center gap-2">
          <p className={`text-sm font-medium truncate ${checked ? 'text-white' : 'text-gray-500 line-through'}`}>
            {recommendation.indicator_name}
          </p>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0 ${signalStyle.className}`}>
            {signalStyle.text}
          </span>
        </div>

        {/* 추천 이유 */}
        {recommendation.why && (
          <div className={`mt-1.5 px-2 py-1.5 rounded-md ${checked ? 'bg-gray-800/60' : 'bg-gray-900/40'}`}>
            <p className={`text-[11px] leading-relaxed ${checked ? 'text-gray-300' : 'text-gray-600'}`}>
              {recommendation.why}
            </p>
          </div>
        )}

        {/* 전제 연결 */}
        {recommendation.premise_title && (
          <p className="text-[10px] text-gray-500 mt-1.5">
            전제: {recommendation.premise_title}
          </p>
        )}
      </div>
    </button>
  )
}
