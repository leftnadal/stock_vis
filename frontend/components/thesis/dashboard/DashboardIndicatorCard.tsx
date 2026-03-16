'use client'

import { ArrowIndicator } from '@/components/thesis/common/ArrowIndicator'
import { AlertTriangle } from 'lucide-react'
import { TREND_CONFIG } from '@/lib/thesis/constants'
import { sanitizeHexColor } from '@/lib/thesis/utils'
import type { DashboardIndicator } from '@/lib/thesis/types'

interface Props {
  indicator: DashboardIndicator
}

export function DashboardIndicatorCard({ indicator }: Props) {
  const trend = TREND_CONFIG[indicator.trend] ?? TREND_CONFIG.stable
  const TrendIcon = trend.icon
  const safeColor = sanitizeHexColor(indicator.color)

  // previous_degree 있으면 방향 포함 라벨, 없으면 간결 라벨
  const trendLabel =
    indicator.previous_degree !== null ? trend.labelWithDelta : trend.label

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
      <div className="flex flex-col items-center gap-2">
        {/* 화살표 */}
        <ArrowIndicator degree={indicator.arrow_degree} size="lg" />

        {/* 지표명 */}
        <p className="text-white text-sm font-medium truncate w-full text-center">
          {indicator.name}
        </p>

        {/* 라벨 (백엔드 계산값, hex 검증 후 사용) */}
        <span className="text-xs" style={{ color: safeColor }}>
          {indicator.label}
        </span>

        {/* 트렌드 */}
        <div className={`flex items-center gap-1 ${trend.className}`}>
          <TrendIcon size={12} />
          <span className="text-[10px]">{trendLabel}</span>
        </div>

        {/* 극단 변동 경고 */}
        {indicator.is_extreme_vol && (
          <div className="flex items-center gap-1 text-red-400">
            <AlertTriangle size={10} />
            <span className="text-[10px]">급변동</span>
          </div>
        )}
      </div>

      {/* 전제 */}
      {indicator.premise_name && (
        <p className="text-[10px] text-gray-600 text-center mt-2 truncate">
          {indicator.premise_name}
        </p>
      )}
    </div>
  )
}
