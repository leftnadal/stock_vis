'use client'

import { X } from 'lucide-react'
import type { LLMIndicatorRecommendation } from '@/lib/thesis/types'

const SIGNAL_TYPE_LABELS: Record<string, { text: string; className: string }> = {
  leading: { text: '선행', className: 'text-blue-400 bg-blue-900/30' },
  coincident: { text: '동행', className: 'text-gray-400 bg-gray-800' },
  lagging: { text: '후행', className: 'text-amber-400 bg-amber-900/30' },
}

interface IndicatorCardProps {
  recommendation: LLMIndicatorRecommendation
  onRemove?: () => void
}

export function IndicatorCard({ recommendation, onRemove }: IndicatorCardProps) {
  const signalStyle = SIGNAL_TYPE_LABELS[recommendation.signal_type] ?? SIGNAL_TYPE_LABELS.coincident

  return (
    <div className="flex items-start gap-3 p-3 bg-gray-900 border border-gray-800 rounded-xl group">
      {/* 매칭 상태 */}
      <span className="flex-shrink-0 mt-0.5 text-sm">
        {recommendation.auto_matched ? '\u2705' : '\u26A0\uFE0F'}
      </span>

      <div className="min-w-0 flex-1">
        {/* 지표명 + signal_type 뱃지 */}
        <div className="flex items-center gap-2">
          <p className="text-sm text-white font-medium truncate">
            {recommendation.indicator_name}
          </p>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0 ${signalStyle.className}`}>
            {signalStyle.text}
          </span>
        </div>

        {/* why */}
        <p className="text-xs text-gray-400 mt-1 line-clamp-2">
          {recommendation.why}
        </p>

        {/* 전제 연결 */}
        {recommendation.premise_title && (
          <p className="text-[10px] text-gray-500 mt-1">
            {recommendation.premise_title}
          </p>
        )}
      </div>

      {/* 삭제 버튼 */}
      {onRemove && (
        <button
          onClick={onRemove}
          className="flex-shrink-0 p-1 text-gray-600 hover:text-gray-300
                     opacity-0 group-hover:opacity-100 transition-opacity"
          aria-label="지표 제거"
        >
          <X size={14} />
        </button>
      )}
    </div>
  )
}
