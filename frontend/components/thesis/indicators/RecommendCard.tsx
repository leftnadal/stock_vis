'use client'

import { Plus, Check, Sparkles } from 'lucide-react'
import { TYPE_LABELS, DIRECTION_LABELS } from '@/lib/thesis/types'
import type { RecommendedIndicator } from '@/lib/thesis/types'

interface Props {
  indicator: RecommendedIndicator
  onAdd: () => void
  added: boolean
  isAdding?: boolean
}

export function RecommendCard({ indicator, onAdd, added, isAdding }: Props) {
  const typeLabel = TYPE_LABELS[indicator.indicator_type] ?? indicator.indicator_type
  const dirLabel = DIRECTION_LABELS[indicator.support_direction] ?? DIRECTION_LABELS.positive

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
      <div className="flex items-start gap-3">
        {/* AI 마크 */}
        <div className="flex-shrink-0 pt-0.5">
          <Sparkles size={16} className="text-purple-400" />
        </div>

        {/* 내용 */}
        <div className="flex-1 min-w-0">
          <p className="text-white text-sm font-medium">{indicator.name}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] px-2 py-0.5 rounded-full text-gray-400 bg-gray-800">
              {typeLabel}
            </span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${dirLabel.className}`}>
              {dirLabel.text}
            </span>
            <span className="text-[10px] text-gray-600">{indicator.data_source}</span>
          </div>
          <p className="text-xs text-gray-500 mt-2 leading-relaxed">
            {indicator.reason}
          </p>
        </div>

        {/* 추가 버튼 */}
        <button
          onClick={onAdd}
          disabled={added || isAdding}
          className={`flex-shrink-0 p-2.5 rounded-xl transition-all
                     ${added
                       ? 'bg-green-900/30 text-green-400'
                       : isAdding
                         ? 'bg-gray-800 text-gray-600'
                         : 'bg-blue-600 text-white active:scale-[0.95]'}`}
          aria-label={added ? '추가됨' : '지표 추가'}
        >
          {added ? <Check size={16} /> : <Plus size={16} />}
        </button>
      </div>
    </div>
  )
}
