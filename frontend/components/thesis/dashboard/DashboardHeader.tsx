'use client'

import { ThesisBadge } from '@/components/thesis/common/ThesisBadge'
import { scoreToBadgeState } from '@/lib/thesis/utils'
import type { DashboardThesis } from '@/lib/thesis/types'

interface Props {
  thesis: DashboardThesis
}

export function DashboardHeader({ thesis }: Props) {
  const badgeState = scoreToBadgeState(thesis.overall_score, thesis.status)

  return (
    <div className="text-center space-y-3">
      <h2 className="text-white text-lg font-bold px-4">{thesis.title}</h2>
      <div className="flex items-center justify-center gap-3">
        <ThesisBadge state={badgeState} direction={thesis.direction} />
        <span className="text-gray-500 text-xs">
          {thesis.days_active}일째 관제 중
        </span>
      </div>
    </div>
  )
}
