'use client'

import type { DashboardIndicator } from '@/lib/thesis/types'
import { formatRawValue, formatChangePct, supportLabel, formatAsofDate } from '@/lib/thesis/utils'

interface Props {
  indicator: DashboardIndicator
}

export function RealValueIndicatorCard({ indicator }: Props) {
  const value = formatRawValue(indicator.raw_value, indicator.raw_value_unit)
  const change = formatChangePct(indicator.change_pct)
  const support = supportLabel(indicator.score)
  const asofLabel = formatAsofDate(indicator.raw_value_asof)

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
      <div className="flex flex-col gap-1.5">
        {/* 지표명 + 기준일 */}
        <div className="flex items-baseline justify-between gap-1">
          <p className="text-gray-400 text-xs truncate">
            {indicator.name}
          </p>
          {asofLabel && (
            <span className="text-[10px] text-gray-600 whitespace-nowrap flex-shrink-0">
              {asofLabel}
            </span>
          )}
        </div>

        {/* 실제 값 */}
        <p className="text-white text-xl font-bold tracking-tight">
          {value}
        </p>

        {/* 변동률 */}
        <span className={`text-sm ${change.colorClass}`}>
          {change.text}
        </span>

        {/* 지지/반박/중립 */}
        <div className="flex items-center gap-1.5">
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${
            support.colorClass.replace('text-', 'bg-')
          }`} />
          <span className={`text-xs ${support.colorClass}`}>
            {support.text}
          </span>
        </div>

        {/* 전제 */}
        {indicator.premise_name && (
          <p className="text-[10px] text-gray-600 truncate mt-0.5">
            {indicator.premise_name}
          </p>
        )}
      </div>
    </div>
  )
}
