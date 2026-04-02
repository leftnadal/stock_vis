'use client'

import type { DashboardIndicator } from '@/lib/thesis/types'
import { formatRawValue, formatChangePct, supportLabel, formatAsofDate } from '@/lib/thesis/utils'
import { QuarterlySparkline } from './QuarterlySparkline'

interface Props {
  indicator: DashboardIndicator
}

export function RealValueIndicatorCard({ indicator }: Props) {
  const value = formatRawValue(indicator.raw_value, indicator.raw_value_unit)
  const change = formatChangePct(indicator.change_pct)
  const support = supportLabel(indicator.score)

  const isQuarterly = indicator.is_quarterly
  const hasHistory = isQuarterly && indicator.quarterly_history && indicator.quarterly_history.length > 0

  // 기준일 라벨: 분기 지표면 fiscal_label, 아니면 asof 날짜
  const dateLabel = isQuarterly
    ? indicator.fiscal_label
    : formatAsofDate(indicator.raw_value_asof)

  // 변동률 접두사: QoQ / YoY
  const changePrefix = isQuarterly && indicator.comparison_type
    ? indicator.comparison_type === 'yoy' ? 'YoY ' : 'QoQ '
    : ''

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
      <div className="flex flex-col gap-1.5">
        {/* 지표명 + 기준일 */}
        <div className="flex items-baseline justify-between gap-1">
          <p className="text-gray-400 text-xs truncate">
            {indicator.name}
          </p>
          {dateLabel && (
            <span className={`text-[10px] whitespace-nowrap flex-shrink-0 ${
              isQuarterly && !hasHistory ? 'text-gray-600' : 'text-gray-500'
            }`}>
              {dateLabel}
            </span>
          )}
        </div>

        {/* 실제 값 */}
        <p className="text-white text-xl font-bold tracking-tight">
          {value}
        </p>

        {/* 변동률 (QoQ/YoY prefix 포함) */}
        <span className={`text-sm ${change.colorClass}`}>
          {changePrefix}{change.text}
        </span>

        {/* 분기 스파크라인 */}
        {hasHistory && (
          <QuarterlySparkline
            history={indicator.quarterly_history!}
            unit={indicator.raw_value_unit}
          />
        )}

        {/* 지지/반박/중립 */}
        <div className="flex items-center gap-1.5">
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${
            support.colorClass.replace('text-', 'bg-')
          }`} />
          <span className={`text-xs ${support.colorClass}`}>
            {support.text}
          </span>
        </div>

        {/* 지표 설명 */}
        {indicator.description && (
          <p className="text-[10px] text-gray-600 truncate mt-0.5" title={indicator.description}>
            {indicator.description}
          </p>
        )}

        {/* 가설 관계성 */}
        {indicator.recommendation_reason && (
          <p className="text-[10px] text-blue-400/50 truncate" title={indicator.recommendation_reason}>
            {indicator.recommendation_reason}
          </p>
        )}
      </div>
    </div>
  )
}
