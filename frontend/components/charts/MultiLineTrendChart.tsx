'use client'

/**
 * MP2-TREND 공용 멀티라인 시계열 차트 (1호 — 이후 적용처가 전부 이 형태로 꽂음).
 *
 * D-TREND-TOOLTIP: 플로팅 툴팁 금지. 크로스헤어(세로선 + 강조라인 도트) + 차트 하단 고정
 *   리드아웃(강조 라인만). 짚지 않으면 pinLatest로 최신일 값 표시. 그래프 위를 가리는 요소 0.
 * D-TREND-BASELINE: overlays(고정선/파생선/밴드/전환일 세로선)는 **타입 계약만** — 1호 렌더 0(2·3호 소관).
 * 팔레트: trendPalette.ts 1곳(신규 hex 산개 금지). 적용처 color 지정 시 우선.
 * FE 값 재계산 금지 — 서버 point.value 그대로. range 토글은 표시 범위 슬라이스만.
 */
import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from 'recharts'

import { TREND_MUTED, trendColor } from './trendPalette'

export interface TrendPoint {
  date: string
  value: number
  /** 리드아웃 부기 텍스트(적용처 공급, 예: "강도 +2.1%"). 컴포넌트는 표시만. */
  note?: string
}

export interface TrendSeries {
  key: string
  label: string
  color?: string
  points: TrendPoint[]
}

/** ⚠ 1호는 타입 계약만 — 렌더 미구현(2·3호 소관). */
export interface TrendOverlays {
  vlines?: { date: string; label?: string }[]
  hlines?: { value: number; label?: string }[]
  bands?: { from: number; to: number; label?: string }[]
  refSeries?: TrendSeries[]
}

interface MultiLineTrendChartProps {
  series: TrendSeries[]
  yAxis?: {
    inverted?: boolean
    domain?: [number | 'auto', number | 'auto']
    tickFormat?: (v: number) => string
  }
  ranges?: number[]
  emphasis?: { default?: string[]; legendToggle?: boolean }
  overlays?: TrendOverlays // 미사용(계약만)
  readout?: { pinLatest?: boolean }
  height?: number
}

function mmdd(iso: string): string {
  // 서버 ISO 날짜 → MM-DD 표시(연산 아님, 포맷만).
  const s = iso.slice(0, 10)
  return s.length >= 10 ? s.slice(5) : s
}

export function MultiLineTrendChart({
  series,
  yAxis,
  ranges = [7, 30],
  emphasis,
  readout = { pinLatest: true },
  height = 260,
}: MultiLineTrendChartProps) {
  const [activeRange, setActiveRange] = useState<number>(ranges[0] ?? 7)
  const [activeDate, setActiveDate] = useState<string | null>(null)
  const [emphasized, setEmphasized] = useState<Set<string>>(
    () => new Set(emphasis?.default ?? series.map((s) => s.key)),
  )

  const colorOf = useMemo(() => {
    const m = new Map<string, string>()
    series.forEach((s, i) => m.set(s.key, s.color ?? trendColor(i)))
    return m
  }, [series])

  // 전 시리즈 통합 날짜(오름차순) → 최근 activeRange개만 표시.
  const allDates = useMemo(() => {
    const set = new Set<string>()
    series.forEach((s) => s.points.forEach((p) => set.add(p.date)))
    return Array.from(set).sort()
  }, [series])
  const shownDates = useMemo(
    () => allDates.slice(Math.max(0, allDates.length - activeRange)),
    [allDates, activeRange],
  )
  const shownSet = useMemo(() => new Set(shownDates), [shownDates])

  // recharts용 merged rows: [{date, [key]:value, ...}]
  const rows = useMemo(() => {
    const byDate = new Map<string, Record<string, number | string>>()
    shownDates.forEach((d) => byDate.set(d, { date: d }))
    series.forEach((s) =>
      s.points.forEach((p) => {
        if (shownSet.has(p.date)) {
          const row = byDate.get(p.date)!
          row[s.key] = p.value
        }
      }),
    )
    return shownDates.map((d) => byDate.get(d)!)
  }, [series, shownDates, shownSet])

  const maxLen = useMemo(
    () => Math.max(0, ...series.map((s) => s.points.filter((p) => shownSet.has(p.date)).length)),
    [series, shownSet],
  )
  const sparse = maxLen <= 2

  // 리드아웃 기준일: 스크럽 중이면 activeDate, 아니면 pinLatest → 최신 표시일.
  const readoutDate = activeDate ?? (readout.pinLatest ? shownDates[shownDates.length - 1] ?? null : null)

  const valueAt = (s: TrendSeries, date: string | null): TrendPoint | null => {
    if (!date) return null
    return s.points.find((p) => p.date === date) ?? null
  }

  const toggleEmphasis = (key: string) => {
    if (emphasis?.legendToggle === false) return
    setEmphasized((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const emphasizedSeries = series.filter((s) => emphasized.has(s.key))

  return (
    <div data-testid="trend-chart" className="w-full">
      {/* 범위 토글 */}
      <div className="flex items-center gap-1 mb-1">
        {ranges.map((r) => (
          <button
            key={r}
            type="button"
            data-testid={`trend-range-${r}`}
            onClick={() => setActiveRange(r)}
            className={`text-xs rounded px-2 py-0.5 border ${
              activeRange === r
                ? 'bg-slate-800 text-white border-slate-800'
                : 'bg-white text-slate-600 border-slate-200'
            }`}
          >
            {r}일
          </button>
        ))}
        {sparse ? (
          <span data-testid="trend-sparse" className="text-xs text-slate-400 ml-2">
            데이터 축적 중
          </span>
        ) : null}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={rows}
          margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
          onMouseMove={(state: { activeLabel?: string | number } | null) => {
            const l = state?.activeLabel
            setActiveDate(typeof l === 'string' ? l : null)
          }}
          onMouseLeave={() => setActiveDate(null)}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="date" tickFormatter={mmdd} tick={{ fontSize: 10 }} minTickGap={20} />
          <YAxis
            reversed={yAxis?.inverted}
            domain={yAxis?.domain ?? ['auto', 'auto']}
            tickFormatter={yAxis?.tickFormat}
            tick={{ fontSize: 10 }}
            width={32}
            allowDecimals={false}
          />
          {/* 크로스헤어 세로선(플로팅 툴팁 대체) */}
          {readoutDate ? (
            <ReferenceLine x={readoutDate} stroke="#94a3b8" strokeDasharray="2 2" />
          ) : null}
          {series.map((s) => {
            const on = emphasized.has(s.key)
            return (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={on ? colorOf.get(s.key) : TREND_MUTED}
                strokeWidth={on ? 2 : 1}
                strokeOpacity={on ? 1 : 0.5}
                dot={false}
                activeDot={false}
                isAnimationActive={false}
                connectNulls
              />
            )
          })}
          {/* 크로스헤어 도트: 강조 라인만, readout 기준일 값 위치 */}
          {readoutDate
            ? emphasizedSeries.map((s) => {
                const pt = valueAt(s, readoutDate)
                if (pt == null) return null
                return (
                  <ReferenceDot
                    key={`dot-${s.key}`}
                    x={readoutDate}
                    y={pt.value}
                    r={3}
                    fill={colorOf.get(s.key)}
                    stroke="#fff"
                    strokeWidth={1}
                  />
                )
              })
            : null}
        </LineChart>
      </ResponsiveContainer>

      {/* 하단 고정 리드아웃(강조 라인만) — 그래프 위 박스 0 */}
      <div data-testid="trend-readout" className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
        <span className="text-slate-400">{readoutDate ? mmdd(readoutDate) : '—'}</span>
        {emphasizedSeries.map((s) => {
          const pt = valueAt(s, readoutDate)
          return (
            <span key={`ro-${s.key}`} data-testid={`trend-readout-${s.key}`} className="text-slate-700">
              <span
                className="inline-block w-2 h-2 rounded-full mr-1 align-middle"
                style={{ backgroundColor: colorOf.get(s.key) }}
              />
              {s.label}
              {pt ? (
                <>
                  {' '}
                  {yAxis?.tickFormat ? yAxis.tickFormat(pt.value) : pt.value}
                  {pt.note ? ` · ${pt.note}` : ''}
                </>
              ) : (
                ' —'
              )}
            </span>
          )
        })}
      </div>

      {/* 범례(강조 토글) */}
      {emphasis?.legendToggle !== false ? (
        <div data-testid="trend-legend" className="mt-2 flex flex-wrap gap-1">
          {series.map((s) => {
            const on = emphasized.has(s.key)
            return (
              <button
                key={`lg-${s.key}`}
                type="button"
                data-testid={`trend-legend-${s.key}`}
                aria-pressed={on}
                onClick={() => toggleEmphasis(s.key)}
                className={`text-xs rounded px-1.5 py-0.5 border ${
                  on ? 'border-slate-300 bg-white text-slate-800' : 'border-slate-200 bg-slate-50 text-slate-400'
                }`}
              >
                <span
                  className="inline-block w-2 h-2 rounded-full mr-1 align-middle"
                  style={{ backgroundColor: on ? colorOf.get(s.key) : TREND_MUTED }}
                />
                {s.label}
              </button>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
