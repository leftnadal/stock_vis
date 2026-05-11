'use client'

import { useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { useAllIndicatorReadings } from '@/lib/thesis/queries'
import { formatRawValue } from '@/lib/thesis/utils'
import { CHART_COLORS } from '@/lib/thesis/constants'
import type { DashboardIndicator, ChartPeriod } from '@/lib/thesis/types'

interface Props {
  thesisId: string
  indicators: DashboardIndicator[]
  period: ChartPeriod
}

export function IndividualMiniCharts({ thesisId, indicators, period }: Props) {
  // 분기 지표는 일간 미니차트에서 제외
  const dailyIndicators = useMemo(
    () => indicators.filter((i) => !i.is_quarterly),
    [indicators],
  )
  const ids = useMemo(() => dailyIndicators.map((i) => i.id), [dailyIndicators])
  const results = useAllIndicatorReadings(thesisId, ids, period)

  return (
    <div className="space-y-4">
      {dailyIndicators.map((ind, idx) => {
        const result = results[idx]
        const readings = result?.data?.readings ?? []
        const unit = result?.data?.unit ?? ind.raw_value_unit
        const color = CHART_COLORS[idx % CHART_COLORS.length]
        const gradientId = `gradient-${ind.id}`

        // period에 맞는 readings만 표시
        const chartData = readings
          .filter((r) => r.raw_value != null)
          .slice(-period)
          .map((r) => ({
            date: format(parseISO(r.asof), 'MM/dd'),
            value: r.raw_value as number,
          }))

        if (chartData.length === 0) return null

        return (
          <div key={ind.id}>
            <p className="text-xs text-gray-500 mb-1">
              {ind.name} ({unit})
            </p>
            <ResponsiveContainer width="100%" height={100}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="date"
                  stroke="#6B7280"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="#6B7280"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  width={55}
                  tickFormatter={(v: number) => formatRawValue(v, unit)}
                  domain={['auto', 'auto']}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: '1px solid #374151',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: '#9CA3AF' }}
                  formatter={(v: number) => [formatRawValue(v, unit), ind.name]}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={color}
                  strokeWidth={1.5}
                  fillOpacity={1}
                  fill={`url(#${gradientId})`}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )
      })}
    </div>
  )
}
