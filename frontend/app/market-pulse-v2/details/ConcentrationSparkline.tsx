'use client'

import type { ConcentrationHistoryPoint } from '@/lib/api/marketPulseV2'
import { CONCENTRATION_TREND, concentrationBand, concentrationTrend } from '../meaning'

/** SVG 좌표 산출 — 값 배열 → [x,y] 폴리라인(가짜 0 패딩 없음, 정규화 min~max). */
export function sparkPoints(values: number[], width = 200, height = 40, pad = 3): string {
  const finite = values.filter((v) => Number.isFinite(v))
  if (finite.length === 0) return ''
  const min = Math.min(...finite)
  const max = Math.max(...finite)
  const span = max - min || 1
  const n = values.length
  const stepX = n > 1 ? (width - pad * 2) / (n - 1) : 0
  return values
    .map((v, i) => {
      const x = pad + i * stepX
      const y = pad + (height - pad * 2) * (1 - (v - min) / span)
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

/**
 * MP-UX-S5 Part B — 집중도 30일 스파크라인 (history_30d 데이터원, FE only).
 * top10_weight 추세선 + 마지막 점 강조 + 추세 주석(meaning.ts 단일소스).
 * history 없음/공백은 호출부(ConcentrationDetail)에서 가드 — 합성 0.
 */
export function ConcentrationSparkline({ history }: { history: ConcentrationHistoryPoint[] }) {
  if (!history || history.length === 0) {
    return <p className="text-xs text-slate-400">집중도 이력 데이터 없음</p>
  }

  const top10s = history.map((h) => h.top10)
  const W = 200
  const H = 40
  const points = sparkPoints(top10s, W, H)
  const last = history[history.length - 1]
  const lastBand = concentrationBand(last.top10)
  const trend = concentrationTrend(top10s)

  // 1점 데이터 graceful: 선 대신 점만, 추세 주석 생략
  const single = history.length < 2

  let annotation: string
  if (single) {
    annotation = `데이터 ${history.length}일 — 추세 산출 보류`
  } else if (trend) {
    const t = CONCENTRATION_TREND[trend]
    annotation = `최근 ${history.length}일 ${t.label} ${t.arrow}`
  } else {
    annotation = `최근 ${history.length}일`
  }

  // 마지막 점 좌표(강조용)
  const pad = 3
  const finite = top10s.filter((v) => Number.isFinite(v))
  const min = Math.min(...finite)
  const max = Math.max(...finite)
  const span = max - min || 1
  const lastX = single ? W / 2 : W - pad
  const lastY = pad + (H - pad * 2) * (1 - (last.top10 - min) / span)

  return (
    <div className="grid gap-1">
      <p className="text-xs text-slate-500">최근 {history.length}일 상위10 비중 추세</p>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label={`집중도(상위10 비중) 스파크라인, ${annotation}`}
        preserveAspectRatio="none"
      >
        {!single ? (
          <polyline points={points} fill="none" stroke="currentColor" className="text-indigo-500" strokeWidth={1.5} />
        ) : null}
        <circle cx={lastX} cy={lastY} r={2.5} className="fill-indigo-600" />
      </svg>
      <div className="flex items-center justify-between text-[10px] text-slate-400">
        <span>{history[0].date}</span>
        <span>{last.date} (오늘)</span>
      </div>
      <p className="text-xs text-slate-700">
        {annotation}
        {lastBand ? ` · 현재 ${lastBand.label}` : ''}
      </p>
    </div>
  )
}
