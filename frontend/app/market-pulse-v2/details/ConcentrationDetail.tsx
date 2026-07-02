'use client'

import React, { useMemo } from 'react'
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import type { PieLabelRenderProps } from 'recharts'

import { translate } from '@/lib/i18n/marketPulse'
import type { ConcentrationDetail as Detail } from '@/lib/api/marketPulseV2'
import { ConcentrationSparkline } from './ConcentrationSparkline'

const COLORS = [
  'rgb(99 102 241)', 'rgb(14 165 233)', 'rgb(34 197 94)',
  'rgb(245 158 11)', 'rgb(244 63 94)', 'rgb(168 85 247)',
  'rgb(16 185 129)', 'rgb(234 88 12)', 'rgb(217 70 239)', 'rgb(59 130 246)',
]

// ── 커스텀 leader-line 외부 라벨 ─────────────────────────────────────────
// A3-TAIL rev2: 전역 가변 제거 + 양방향 nudge + 상단 클리핑 방지.
// 배치는 ConcentrationDetail 컴포넌트가 useMemo로 렌더 전 1회 계산한 뒤
// renderPieLabel은 해당 맵을 읽기만 한다 → Strict Mode/다중 인스턴스 안전.

const DEG_TO_RAD = Math.PI / 180
const MIN_GAP = 14        // 최소 라벨 수직 간격 (px)
const R1_OFFSET = 6       // 조각 외곽 기준점 여유 (px)
const R2_OFFSET = 22      // 꺾임점 여유 (px)
const TX_OFFSET = 14      // 텍스트 수평 연장 (px)

/** recharts midAngle은 도(degree) 단위, CCW=양수. cos/sin 계산용 */
export function polarToCart(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = angleDeg * DEG_TO_RAD
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) }
}

/**
 * 단일 조각의 라벨 배치 좌표 계산 (순수 함수, nudge 미적용).
 * Returns null when value < threshold.
 */
export interface LabelLayout {
  /** 조각 외곽 기준점 */
  px1: { x: number; y: number }
  /** leader 꺾임점 */
  px2: { x: number; y: number }
  /** 텍스트 앵커 x */
  tx: number
  /** 텍스트 y (nudge 미적용) */
  ty: number
  textAnchor: 'start' | 'end'
  label: string
  /** cos(midAngle) >= 0 → right side */
  isRight: boolean
  /** midAngle (원본 각도, nudge 정렬용) */
  midAngle: number
}

export function computeLabelLayout(
  cx: number,
  cy: number,
  outerRadius: number,
  midAngle: number,
  value: number,
  threshold = 0,
): LabelLayout | null {
  if (value < threshold) return null

  const label = `${(value * 100).toFixed(1)}%`
  const RAD_MID = midAngle * DEG_TO_RAD

  const cosA = Math.cos(RAD_MID)
  const sinA = Math.sin(RAD_MID)
  const isRight = cosA >= 0

  const r1 = outerRadius + R1_OFFSET
  const px1 = { x: cx + r1 * cosA, y: cy - r1 * sinA }

  const r2 = outerRadius + R2_OFFSET
  const px2 = { x: cx + r2 * cosA, y: cy - r2 * sinA }

  const tx = isRight ? px2.x + TX_OFFSET : px2.x - TX_OFFSET

  return { px1, px2, tx, ty: px2.y, textAnchor: isRight ? 'start' : 'end', label, isRight, midAngle }
}

/**
 * 전체 데이터에서 라벨 배치를 1회 계산하는 배치 함수.
 * nudge를 양방향(위/아래)으로 적용하고, y_min 경계 가드로 클리핑 방지.
 *
 * 전략:
 * 1. 각 데이터 항목에서 computeLabelLayout으로 기본 좌표 계산
 * 2. 좌/우 사이드별로 midAngle 기준 위→아래 순서로 정렬
 * 3. 각 사이드 내에서 y가 너무 가까우면 현재 item 기준 아래 방향으로 min
 *    단, y_min 경계(상단 클리핑 한계) 미만이 되면 아래로 밀어 경계 내로 유지
 * 4. index → finalY 맵을 반환해 렌더러에서 읽기만 하도록
 */
export function computeAllLabelLayouts(
  data: { name: string; value: number }[],
  cx: number,
  cy: number,
  outerRadius: number,
  /** recharts가 건네주는 midAngle 배열 (없을 경우 빈 배열) */
  midAngles: number[],
  /** SVG 높이 (클리핑 하한) */
  svgHeight: number,
  /** 상단 여백 여유 (클리핑 상한 = -margin) */
  yMinMargin = 10,
): Map<number, number> {
  // y 좌표 하한(SVG 안): cy 기준 좌표이므로 SVG y는 cy + layout.ty
  // recharts SVG의 y 범위: 0 ~ svgHeight
  // layout.ty는 SVG 좌표 직접값(0~svgHeight 범위)
  const Y_MIN = yMinMargin               // 상단 경계
  const Y_MAX = svgHeight - yMinMargin   // 하단 경계

  const finalYMap = new Map<number, number>()

  // 각 데이터에 대해 기본 레이아웃 계산 (midAngles 없으면 스킵)
  type Entry = { idx: number; layout: LabelLayout }
  const leftEntries: Entry[] = []
  const rightEntries: Entry[] = []

  data.forEach((item, idx) => {
    const midAngle = midAngles[idx]
    if (midAngle === undefined || midAngle === null) return

    const layout = computeLabelLayout(cx, cy, outerRadius, midAngle, item.value)
    if (!layout) return

    if (layout.isRight) {
      rightEntries.push({ idx, layout })
    } else {
      leftEntries.push({ idx, layout })
    }
  })

  // 같은 사이드 내에서 y 오름차순(위→아래) 정렬 → 위에서부터 채워 아래로 밀기
  function sortByY(entries: Entry[]) {
    return [...entries].sort((a, b) => a.layout.ty - b.layout.ty)
  }

  function applyNudge(entries: Entry[]) {
    const sorted = sortByY(entries)
    const placed: number[] = []

    for (const { idx, layout } of sorted) {
      let candidate = layout.ty

      // 이미 배치된 슬롯과 MIN_GAP 이상 떨어지도록 아래 방향 밀기
      // (위→아래 순서로 순회하므로 항상 아래로 밀면 안전)
      let changed = true
      while (changed) {
        changed = false
        for (const placed_y of placed) {
          if (Math.abs(placed_y - candidate) < MIN_GAP) {
            // 아래 방향으로 밀기 (placed_y보다 MIN_GAP 아래)
            candidate = placed_y + MIN_GAP
            changed = true
          }
        }
      }

      // 상단/하단 경계 클리핑 가드
      candidate = Math.max(Y_MIN, Math.min(Y_MAX, candidate))

      placed.push(candidate)
      finalYMap.set(idx, candidate)
    }
  }

  applyNudge(leftEntries)
  applyNudge(rightEntries)

  return finalYMap
}

export function ConcentrationDetail({ payload, labels }: { payload: Detail; labels?: Record<string, string> }) {
  if (!payload.available) {
    return <p className="text-sm text-slate-500">집중도 상세 데이터가 아직 준비되지 않았습니다.</p>
  }

  const holdings = payload.top_holdings ?? []
  const restWeight = Math.max(0, 1 - holdings.reduce((s, h) => s + h.weight, 0))
  const data = useMemo(() => [
    ...holdings.map((h) => ({ name: h.symbol, value: h.weight })),
    { name: 'others', value: restWeight },
  ], [holdings, restWeight])

  // 차트 레이아웃 상수 — PieChart가 실제로 결정하는 값이지만
  // recharts의 기본 배치(cx=width/2, cy=height/2)를 근사값으로 사용.
  // 실제 cx/cy는 첫 라벨 콜백에서 덮어씀(아래 참조).
  // height 260→320: 상단 라벨을 위한 여백 확보.
  const CHART_HEIGHT = 320
  const OUTER_RADIUS = 90

  // recharts는 midAngle을 각 조각 콜백에서 건네주는데,
  // 배치 계산은 렌더 전에 1회만 해야 한다.
  // 해결책: midAngle + cx/cy를 첫 렌더 콜백에서 캡처하는 ref를 두고
  // 두 번째 렌더 패스에서 배치 맵을 사용한다.
  // 그러나 recharts는 단일 렌더 패스이므로, 대신 각도에서 직접 계산한다.
  //
  // recharts Pie는 startAngle=0(3시 방향), 반시계 방향으로 데이터를 쌓는다.
  // midAngle = startAngle + (누적각도 + 해당조각각도/2)
  // 이를 미리 계산해 배치 맵에 사용.
  const midAnglesComputed = useMemo(() => {
    const total = data.reduce((s, d) => s + d.value, 0)
    const startAngle = 0  // recharts 기본 startAngle (3시 방향 = 0도)
    const angles: number[] = []
    let accumulated = startAngle
    for (const item of data) {
      const sweep = (item.value / total) * 360
      angles.push(accumulated + sweep / 2)
      accumulated += sweep
    }
    return angles
  }, [data])

  // 실제 cx/cy는 ResponsiveContainer 크기에 따라 달라지므로
  // 라벨 콜백 첫 호출 시 캡처해 배치 맵을 재계산하는 방식 사용.
  // 성능 최적화: 맵을 렌더마다 재생성 방지를 위해 ref 패턴.
  const layoutCacheRef = React.useRef<{
    cx: number; cy: number; map: Map<number, number>
  } | null>(null)

  // 라벨 배치 맵을 cx/cy가 처음 결정되면 계산 (이후 변경 없으면 재사용)
  function getOrBuildLayoutMap(cx: number, cy: number): Map<number, number> {
    const cache = layoutCacheRef.current
    if (cache && cache.cx === cx && cache.cy === cy) {
      return cache.map
    }
    const map = computeAllLabelLayouts(
      data,
      cx,
      cy,
      OUTER_RADIUS,
      midAnglesComputed,
      CHART_HEIGHT,
      10,
    )
    layoutCacheRef.current = { cx, cy, map }
    return map
  }

  // recharts label 콜백 — 전역 가변 없음, ref 캐시만 사용
  function renderLabel(props: PieLabelRenderProps): React.ReactElement | null {
    const { cx, cy, outerRadius, midAngle, value, index } = props

    const cxN = typeof cx === 'number' ? cx : 0
    const cyN = typeof cy === 'number' ? cy : 0
    const outerR = typeof outerRadius === 'number' ? outerRadius : OUTER_RADIUS
    const mid = typeof midAngle === 'number' ? midAngle : 0
    const val = typeof value === 'number' ? value : 0
    const idx = typeof index === 'number' ? index : 0

    const layoutMap = getOrBuildLayoutMap(cxN, cyN)
    const layout = computeLabelLayout(cxN, cyN, outerR, mid, val, 0)
    if (!layout) return null

    // nudge된 y — 배치 맵에 있으면 사용, 없으면 기본값
    const nudgedY = layoutMap.get(idx) ?? layout.ty

    const pathD = [
      `M ${layout.px1.x.toFixed(1)} ${layout.px1.y.toFixed(1)}`,
      `L ${layout.px2.x.toFixed(1)} ${nudgedY.toFixed(1)}`,
      `L ${layout.tx.toFixed(1)} ${nudgedY.toFixed(1)}`,
    ].join(' ')

    return (
      <g key={`label-${idx}`}>
        <path
          d={pathD}
          fill="none"
          stroke="rgb(148 163 184)"
          strokeWidth={1}
        />
        <text
          x={layout.tx}
          y={nudgedY}
          dy="0.35em"
          textAnchor={layout.textAnchor}
          fill="rgb(51 65 85)"
          fontSize={10}
        >
          {layout.label}
        </text>
      </g>
    )
  }

  return (
    <div className="grid gap-4">
      <header className="grid grid-cols-3 gap-2 text-center">
        <Metric labelKey="metric.top5" fallback="top5" value={payload.top5_weight ?? 0} labels={labels} />
        <Metric labelKey="metric.top10" fallback="top10" value={payload.top10_weight ?? 0} labels={labels} />
        <Metric labelKey="metric.hhi" fallback="HHI" value={payload.hhi ?? 0} digits={4} percent={false} labels={labels} />
      </header>

      {/* MP-UX-S5 Part B: 30일 집중도(상위10 비중) 스파크라인 */}
      {payload.history_30d && payload.history_30d.length > 0 ? (
        <ConcentrationSparkline history={payload.history_30d} />
      ) : null}

      <div>
        <p className="text-xs text-slate-500 mb-1">
          {translate(`universe.${payload.universe}`, labels, payload.universe ?? '')} 상위 10종 + 나머지
        </p>
        {/* height 260→320: 상단 라벨 클리핑 방지 여백 확보 */}
        <div style={{ width: '100%', height: CHART_HEIGHT }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                innerRadius={50}
                outerRadius={OUTER_RADIUS}
                label={renderLabel}
                labelLine={false}
              >
                {data.map((entry, i) => (
                  <Cell key={entry.name} fill={entry.name === 'others' ? 'rgb(203 213 225)' : COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => `${(v * 100).toFixed(2)}%`} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {holdings.length > 0 ? (
        <div>
          <p className="text-xs text-slate-500 mb-1">상위 보유 종목</p>
          <ul className="text-xs text-slate-700 space-y-0.5">
            {holdings.map((h) => (
              <li key={h.symbol} className="flex justify-between border-b border-slate-100 py-0.5">
                <span className="font-mono">{h.symbol}</span>
                <span>{(h.weight * 100).toFixed(2)}%</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

function Metric({
  labelKey, fallback, value, digits = 2, percent = true, labels,
}: {
  labelKey: string
  fallback: string
  value: number
  digits?: number
  percent?: boolean
  labels?: Record<string, string>
}) {
  return (
    <div>
      <p className="text-xs text-slate-500">{translate(labelKey, labels, fallback)}</p>
      <p className="text-base font-semibold text-slate-900">
        {percent ? `${(value * 100).toFixed(digits)}%` : value.toFixed(digits)}
      </p>
    </div>
  )
}
