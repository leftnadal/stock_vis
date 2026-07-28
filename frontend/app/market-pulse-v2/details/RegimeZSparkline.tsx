'use client'

/**
 * MP2-TREND S4 — 국면 성분 z-이상도 스파크라인(raw 변형).
 *
 * raw 스파크라인과 대칭 격자·경량 inline SVG. 다른 점:
 *  - y축 = 0 중심 대칭(±M). 0선 실선, ±2 점선(σ 밴드).
 *  - 초입 저신뢰 구간(date < low_confidence_until) 좌측 음영.
 *  - null(결측·기준불충분) = 선 단절(발명 금지 — 보간 없음).
 * z 값은 payload 그대로(하드코딩 0). insufficient 성분은 상위(셀)가 미렌더 처리.
 */
import type { RegimeZComponent } from '@/lib/api/marketPulseV2'

const W = 132
const H = 44
const PAD = 4
const Z_BAND = 2 // ±2σ 기준선

export function RegimeZSparkline({
  component,
  lowConfidenceUntil,
}: {
  component: RegimeZComponent
  lowConfidenceUntil?: string
}) {
  const series = component.series
  const present = series
    .map((p, i) => (p.z == null ? null : { i, z: p.z }))
    .filter((x): x is { i: number; z: number } => x !== null)

  if (present.length === 0) {
    return (
      <div
        data-testid={`zspark-${component.key}`}
        className="h-11 flex items-center text-[10px] text-slate-400"
      >
        기준 불충분
      </div>
    )
  }

  // 대칭 도메인: 최소 ±3(±2 밴드가 항상 보이게), 실제 최대 |z|까지 확장.
  const maxAbs = Math.max(3, ...present.map((p) => Math.abs(p.z)))
  const yOf = (z: number) => PAD + (H - PAD * 2) * (1 - (z + maxAbs) / (2 * maxAbs))
  const n = series.length
  const stepX = n > 1 ? (W - PAD * 2) / (n - 1) : 0
  const xOf = (i: number) => PAD + i * stepX

  // null 단절: 연속 구간별 polyline 세그먼트.
  const segments: string[] = []
  let cur: string[] = []
  for (const p of series) {
    if (p.z == null) {
      if (cur.length >= 2) segments.push(cur.join(' '))
      cur = []
    } else {
      const idx = series.indexOf(p)
      cur.push(`${xOf(idx).toFixed(1)},${yOf(p.z).toFixed(1)}`)
    }
  }
  if (cur.length >= 2) segments.push(cur.join(' '))

  // 저신뢰 초입 음영: date < lowConfidenceUntil 인 마지막 인덱스까지.
  let shadeToIdx = -1
  if (lowConfidenceUntil) {
    for (let i = 0; i < series.length; i++) {
      if (series[i].date < lowConfidenceUntil) shadeToIdx = i
      else break
    }
  }

  const last = present[present.length - 1]

  return (
    <svg
      data-testid={`zspark-${component.key}`}
      width="100%"
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className="block"
    >
      {/* 저신뢰 초입 음영 */}
      {shadeToIdx >= 0 ? (
        <rect
          data-testid={`zspark-shade-${component.key}`}
          x={PAD}
          y={PAD}
          width={Math.max(0, xOf(shadeToIdx) - PAD)}
          height={H - PAD * 2}
          fill="#f1f5f9"
        />
      ) : null}
      {/* ±2σ 점선 */}
      {[Z_BAND, -Z_BAND].map((z) => (
        <line
          key={`band-${z}`}
          data-testid={`zband-${component.key}-${z}`}
          x1={PAD}
          x2={W - PAD}
          y1={yOf(z)}
          y2={yOf(z)}
          stroke="#cbd5e1"
          strokeWidth={1}
          strokeDasharray="3 2"
        />
      ))}
      {/* 0선 실선 */}
      <line
        data-testid={`zline0-${component.key}`}
        x1={PAD}
        x2={W - PAD}
        y1={yOf(0)}
        y2={yOf(0)}
        stroke="#94a3b8"
        strokeWidth={1}
      />
      {/* z 궤적(세그먼트) */}
      {segments.map((pts, i) => (
        <polyline key={`seg-${i}`} points={pts} fill="none" stroke="#334155" strokeWidth={1.5} />
      ))}
      {/* 최신점 도트 — |z|≥2면 danger 색 */}
      {last ? (
        <circle
          cx={xOf(last.i)}
          cy={yOf(last.z)}
          r={2.2}
          fill={Math.abs(last.z) >= Z_BAND ? '#e11d48' : '#334155'}
        />
      ) : null}
    </svg>
  )
}
