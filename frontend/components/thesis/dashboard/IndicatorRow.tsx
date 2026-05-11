'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import type { DashboardIndicator } from '@/lib/thesis/types'
import { formatRawValue, formatChangePct, supportLabel, formatAsofDate } from '@/lib/thesis/utils'
import { useIndicatorReadings } from '@/lib/thesis/queries'
import { QuarterlySparkline } from './QuarterlySparkline'

const DAILY_PERIODS = [
  { days: 30, label: '1M' },
  { days: 365, label: '1Y' },
  { days: 1095, label: '3Y' },
  { days: 1825, label: '5Y' },
] as const

interface Props {
  thesisId: string
  indicator: DashboardIndicator
}

/** 비교 라벨: 전분기대비 / 전년동기대비 / 전일대비 */
function comparisonLabel(indicator: DashboardIndicator): string {
  if (!indicator.is_quarterly) return '전일대비'
  if (indicator.comparison_type === 'yoy') return '전년동기대비'
  return '전분기대비'
}

/** 기간에 따라 날짜 포맷 변경 */
function formatDateByPeriod(dateStr: string, days: number): string {
  const d = parseISO(dateStr)
  if (days <= 30) return format(d, 'MM/dd')
  if (days <= 365) return format(d, 'yy/MM')
  return format(d, "yy'")
}

export function IndicatorRow({ thesisId, indicator }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [chartDays, setChartDays] = useState(365)

  const value = formatRawValue(indicator.raw_value, indicator.raw_value_unit)
  const change = formatChangePct(indicator.change_pct)
  const support = supportLabel(indicator.score)

  const isQuarterly = indicator.is_quarterly
  const hasHistory = isQuarterly && indicator.quarterly_history && indicator.quarterly_history.length > 0

  const dateLabel = isQuarterly
    ? indicator.fiscal_label
    : formatAsofDate(indicator.raw_value_asof)

  // 일간 지표 차트 데이터 — 토글 펼쳤을 때만 fetch
  const isDaily = !isQuarterly
  const { data: readingsData, isLoading: chartLoading } = useIndicatorReadings(
    thesisId, indicator.id, chartDays, expanded && isDaily,
  )

  // 장기 데이터는 간격을 두고 샘플링 (1Y 이상이면 주간, 3Y 이상이면 월간)
  const sampleInterval = chartDays <= 30 ? 1 : chartDays <= 365 ? 5 : chartDays <= 1095 ? 20 : 40

  const chartData = isDaily && readingsData
    ? readingsData.readings
        .filter((r) => r.raw_value != null)
        .filter((_, i, arr) => i % sampleInterval === 0 || i === arr.length - 1)
        .map((r) => ({
          date: formatDateByPeriod(r.asof, chartDays),
          value: r.raw_value as number,
        }))
    : []

  const chartUnit = readingsData?.unit ?? indicator.raw_value_unit

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
      {/* 메인 행 — 클릭으로 토글 */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-4 py-3 hover:bg-gray-800/50 transition-colors"
      >
        {/* 1행: 이름 + 날짜 + 토글 아이콘 */}
        <div className="flex items-center gap-2 mb-1.5">
          <span className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${
            support.colorClass.replace('text-', 'bg-')
          }`} />
          <span className="text-gray-300 text-sm font-medium truncate flex-1">
            {indicator.name}
          </span>
          {dateLabel && (
            <span className="text-[11px] text-gray-500 flex-shrink-0">
              {dateLabel}
            </span>
          )}
          <ChevronDown
            size={14}
            className={`text-gray-500 flex-shrink-0 transition-transform ${
              expanded ? 'rotate-180' : ''
            }`}
          />
        </div>

        {/* 2행: 값 + 변동률 + 스파크라인 + 지지/반박 */}
        <div className="flex items-center gap-3 pl-4">
          {/* 값 */}
          <span className="text-white text-lg font-bold tracking-tight min-w-[60px]">
            {value}
          </span>

          {/* 변동률 + 비교 라벨 */}
          <div className="flex items-baseline gap-1 min-w-[120px]">
            {indicator.change_pct != null ? (
              <>
                <span className="text-[11px] text-gray-500">
                  {comparisonLabel(indicator)}
                </span>
                <span className={`text-sm font-medium ${change.colorClass}`}>
                  {change.text}
                </span>
              </>
            ) : (
              <span className="text-xs text-gray-600">--</span>
            )}
          </div>

          {/* 분기 스파크라인 — 인라인에는 최근 4분기만 */}
          {hasHistory && (
            <div className="flex-1 max-w-[100px]">
              <QuarterlySparkline
                history={indicator.quarterly_history!.slice(-4)}
                unit={indicator.raw_value_unit}
              />
            </div>
          )}

          {/* 지지/반박 — 오른쪽 끝 */}
          <span className={`text-xs ml-auto flex-shrink-0 ${support.colorClass}`}>
            {support.text}
          </span>
        </div>

        {/* 3행: 전제 */}
        {indicator.premise_name && (
          <p className="text-[11px] text-gray-600 truncate pl-4 mt-1">
            {indicator.premise_name}
          </p>
        )}
      </button>

      {/* 펼침 영역: 설명 + 차트 */}
      {expanded && (
        <div className="border-t border-gray-800 px-4 py-3">
          {/* 지표 설명 + 가설 관계성 */}
          {(indicator.description || indicator.recommendation_reason) && (
            <div className="mb-3 space-y-1">
              {indicator.description && (
                <p className="text-[11px] text-gray-500 leading-relaxed">
                  <span className="text-gray-400 font-medium">지표 </span>
                  {indicator.description}
                </p>
              )}
              {indicator.recommendation_reason && (
                <p className="text-[11px] text-blue-400/70 leading-relaxed">
                  <span className="text-blue-400/90 font-medium">관계 </span>
                  {indicator.recommendation_reason}
                </p>
              )}
            </div>
          )}
          {isDaily ? (
            /* 일간 지표: area chart + period selector */
            <div>
              <div className="flex gap-1.5 mb-2">
                {DAILY_PERIODS.map(({ days, label }) => (
                  <button
                    key={days}
                    onClick={(e) => { e.stopPropagation(); setChartDays(days) }}
                    className={`px-2.5 py-0.5 text-[10px] rounded transition-colors ${
                      chartDays === days
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-800 text-gray-500 hover:bg-gray-700'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {chartLoading ? (
                <div className="flex items-center justify-center py-8">
                  <span className="text-gray-600 text-xs">로딩 중...</span>
                </div>
              ) : chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={160}>
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id={`grad-${indicator.id}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#60A5FA" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#60A5FA" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="date" stroke="#6B7280" fontSize={9} tickLine={false} axisLine={false}
                      interval={chartData.length > 20 ? Math.floor(chartData.length / 6) - 1 : 0}
                    />
                    <YAxis
                      stroke="#6B7280" fontSize={10} tickLine={false} axisLine={false}
                      width={55}
                      tickFormatter={(v: number) => formatRawValue(v, chartUnit)}
                      domain={['auto', 'auto']}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: '#9CA3AF' }}
                      formatter={(v: number) => [formatRawValue(v, chartUnit), indicator.name]}
                    />
                    <Area type="monotone" dataKey="value" stroke="#60A5FA" strokeWidth={1.5} fillOpacity={1} fill={`url(#grad-${indicator.id})`} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-600 text-xs text-center py-6">차트 데이터 없음</p>
              )}
            </div>
          ) : (
            /* 분기 지표: 5개년 area chart */
            hasHistory ? (
              <div>
                <p className="text-[11px] text-gray-500 mb-2">
                  분기별 추이 ({indicator.quarterly_history!.length}분기)
                </p>
                <ResponsiveContainer width="100%" height={140}>
                  <AreaChart data={indicator.quarterly_history!.map((h) => ({
                    label: `Q${h.fq} '${String(h.fy).slice(-2)}`,
                    value: h.value,
                  }))}>
                    <defs>
                      <linearGradient id={`qgrad-${indicator.id}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#60A5FA" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#60A5FA" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="label" stroke="#6B7280" fontSize={9} tickLine={false} axisLine={false}
                      interval={indicator.quarterly_history!.length > 8 ? Math.floor(indicator.quarterly_history!.length / 5) - 1 : 0}
                    />
                    <YAxis
                      stroke="#6B7280" fontSize={10} tickLine={false} axisLine={false}
                      width={50}
                      tickFormatter={(v: number) => formatRawValue(v, indicator.raw_value_unit)}
                      domain={['auto', 'auto']}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: '#9CA3AF' }}
                      formatter={(v: number) => [formatRawValue(v, indicator.raw_value_unit), indicator.name]}
                    />
                    <Area type="monotone" dataKey="value" stroke="#60A5FA" strokeWidth={1.5} fillOpacity={1} fill={`url(#qgrad-${indicator.id})`} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-gray-600 text-xs text-center py-4">분기 히스토리 없음</p>
            )
          )}
        </div>
      )}
    </div>
  )
}
