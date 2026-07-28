'use client'

/**
 * MP2-TREND S3(R1) — 국면 재료 소형 다중 셀 스파크라인.
 *
 * 경량 inline SVG(SectorSparkline 계열 재사용) — 라인 1개 + 컷 hlines(심각도 색).
 * 컷·시계열은 payload 그대로(하드코딩 0). z-score 아님 = raw 값 궤적 + rules.yaml 실제 컷.
 * y-도메인 = series 값 + 컷 값 합집합(컷이 라인 대비 어디인지 보이게).
 */
import type { RegimeComponent } from '@/lib/api/marketPulseV2'
import { DIRECTION_HEX_SIGNED } from '@/components/common/colorSemantics'

const W = 132
const H = 44
const PAD = 4

// 컷 심각도 색(regime tone 계열, SVG stroke hex). late_bull=amber·transition=slate·bear=orange.
// COLOR-STAGE2 정합(선소비 조항): CRISIS = 부정=sky(colorSemantics DIRECTION_HEX_SIGNED.negative) — 위기 축 이동 반영.
//   (LATE_BULL/TRANSITION/BEAR은 STAGE2가 유지한 비-flip축 caution 톤과 동일 — 무변경.)
export const CUT_STROKE: Record<string, string> = {
  LATE_BULL: '#d97706',
  TRANSITION: '#64748b',
  BEAR_CONTRACTION: '#ea580c',
  CRISIS: DIRECTION_HEX_SIGNED.negative,
  BULL_EXPANSION: '#94a3b8',
}

export function RegimeComponentSparkline({ component }: { component: RegimeComponent }) {
  const present = component.series
    .map((p, i) => (p.value == null ? null : { i, v: p.value }))
    .filter((x): x is { i: number; v: number } => x !== null)
  const cutVals = component.cuts.map((c) => c.value)
  const domain = [...present.map((p) => p.v), ...cutVals]

  if (domain.length === 0) {
    return (
      <div data-testid={`spark-${component.key}`} className="h-11 flex items-center text-[10px] text-slate-400">
        데이터 없음
      </div>
    )
  }

  const min = Math.min(...domain)
  const max = Math.max(...domain)
  const span = max - min || 1
  const yOf = (v: number) => PAD + (H - PAD * 2) * (1 - (v - min) / span)
  const n = component.series.length
  const stepX = n > 1 ? (W - PAD * 2) / (n - 1) : 0
  const xOf = (i: number) => PAD + i * stepX

  const linePoints = present.map((p) => `${xOf(p.i).toFixed(1)},${yOf(p.v).toFixed(1)}`).join(' ')
  const last = present[present.length - 1]

  return (
    <svg
      data-testid={`spark-${component.key}`}
      width="100%"
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className="block"
    >
      {/* 컷 hlines — 심각도 색, 점선 */}
      {component.cuts.map((c, i) => (
        <line
          key={`cut-${c.value}-${i}`}
          data-testid={`cut-${component.key}-${c.value}`}
          x1={PAD}
          x2={W - PAD}
          y1={yOf(c.value)}
          y2={yOf(c.value)}
          stroke={CUT_STROKE[c.regime] ?? '#94a3b8'}
          strokeWidth={1}
          strokeDasharray="3 2"
        />
      ))}
      {/* 지표 raw 라인 */}
      {present.length >= 2 ? (
        <polyline points={linePoints} fill="none" stroke="#334155" strokeWidth={1.5} />
      ) : null}
      {/* 최신점 도트 */}
      {last ? <circle cx={xOf(last.i)} cy={yOf(last.v)} r={2} fill="#334155" /> : null}
    </svg>
  )
}
