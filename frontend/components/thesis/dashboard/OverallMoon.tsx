'use client'

import { MoonPhase } from '@/components/thesis/common/MoonPhase'
import type { DashboardThesis } from '@/lib/thesis/types'

interface Props {
  thesis: DashboardThesis
}

export function OverallMoon({ thesis }: Props) {
  return (
    <div className="flex flex-col items-center gap-3 py-4">
      <MoonPhase score={thesis.overall_score} size="lg" />
      <p className="text-gray-300 text-sm font-medium">
        {thesis.overall_label}
      </p>
      <p className="text-gray-600 text-xs">
        종합 점수: {thesis.overall_score != null
          ? `${thesis.overall_score > 0 ? '+' : ''}${thesis.overall_score.toFixed(2)}`
          : '—'}
      </p>
    </div>
  )
}
