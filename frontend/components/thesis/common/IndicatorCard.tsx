'use client'

import { ArrowIndicator } from './ArrowIndicator'
import { degreeToColor } from '@/lib/thesis/utils'
import type { ThesisIndicator } from '@/lib/thesis/types'

interface Props {
  indicator: ThesisIndicator
  onClick?: () => void
}

export function IndicatorCard({ indicator, onClick }: Props) {
  const color = degreeToColor(indicator.current_arrow_degree)

  return (
    <button
      onClick={onClick}
      disabled={!indicator.is_active}
      className={`
        w-full bg-gray-900 border border-gray-700 rounded-xl p-4
        flex flex-col items-center gap-2
        transition-transform active:scale-95
        ${!indicator.is_active
          ? 'opacity-40 cursor-not-allowed'
          : 'hover:border-gray-500 cursor-pointer'
        }
      `}
    >
      <ArrowIndicator degree={indicator.current_arrow_degree} size="lg" />
      <span className="text-white text-sm font-medium truncate w-full text-center">
        {indicator.name}
      </span>
      <span className="text-xs" style={{ color }}>
        {indicator.current_label}
      </span>
    </button>
  )
}
