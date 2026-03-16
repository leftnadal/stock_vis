'use client'

import { ArrowIndicator } from '@/components/thesis/common/ArrowIndicator'
import { Power, Trash2 } from 'lucide-react'
import { TYPE_LABELS, DIRECTION_LABELS } from '@/lib/thesis/types'
import type { ThesisIndicator } from '@/lib/thesis/types'

interface Props {
  indicator: ThesisIndicator
  onToggle: (indicatorId: string, isActive: boolean) => void
  onRemove: (indicatorId: string) => void
  isToggling?: boolean
  isRemoving?: boolean
}

export function IndicatorSetupCard({
  indicator, onToggle, onRemove, isToggling, isRemoving,
}: Props) {
  const typeLabel = TYPE_LABELS[indicator.indicator_type] ?? indicator.indicator_type
  const dirLabel = DIRECTION_LABELS[indicator.support_direction] ?? DIRECTION_LABELS.positive

  return (
    <div
      className={`bg-gray-900 border border-gray-700 rounded-xl p-4 transition-opacity
                  ${!indicator.is_active ? 'opacity-50' : ''}`}
    >
      <div className="flex items-start gap-3">
        {/* 화살표 */}
        <div className="flex-shrink-0 pt-0.5">
          <ArrowIndicator degree={indicator.current_arrow_degree} size="sm" />
        </div>

        {/* 내용 */}
        <div className="flex-1 min-w-0">
          <p className="text-white text-sm font-medium truncate">{indicator.name}</p>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="text-[10px] px-2 py-0.5 rounded-full text-gray-400 bg-gray-800">
              {typeLabel}
            </span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full ${dirLabel.className}`}>
              {dirLabel.text}
            </span>
            <span className="text-[10px] text-gray-600">{indicator.data_source}</span>
          </div>
        </div>

        {/* 액션 버튼 */}
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => onToggle(indicator.id, !indicator.is_active)}
            disabled={isToggling}
            className={`p-2 rounded-lg transition-colors
                       ${indicator.is_active
                         ? 'text-blue-400 hover:bg-blue-900/30'
                         : 'text-gray-600 hover:bg-gray-800'}`}
            aria-label={indicator.is_active ? '비활성화' : '활성화'}
          >
            <Power size={16} />
          </button>
          <button
            onClick={() => onRemove(indicator.id)}
            disabled={isRemoving}
            className="p-2 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-900/20
                       transition-colors"
            aria-label="지표 삭제"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {/* 현재 라벨 */}
      {indicator.is_active && indicator.current_label && (
        <p className="text-[11px] text-gray-500 mt-2 ml-8">
          현재: {indicator.current_label}
        </p>
      )}
    </div>
  )
}
