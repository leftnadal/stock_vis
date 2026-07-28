// 상태밴드 스파크라인 (MON-P3-ALERT §6) — 렌더 전용.
// ⚠️ 임계값 하드코딩 금지: 밴드(min/max)는 API(/monitor/monitors/{id}/sparkline/)가 내려준
// 값만 사용한다. score_to_phase 경계 변경은 BE 엔진이 단일 소스.
import { DIRECTION_HEX_SIGNED } from '@/components/common/colorSemantics'
import type { SparklineBand, SparklinePhase, SparklinePoint } from '@/types/monitor'

interface StateBandSparklineProps {
  series: SparklinePoint[]
  bands: SparklineBand[]
  transitions?: string[]
  width?: number
  height?: number
  className?: string
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// 밴드 배경색: 밝음(긍정, full_moon)→중립(half_moon)→어두움(부정, new_moon) 그라데이션.
// colorSemantics DIRECTION_HEX_SIGNED(긍정부정 축) 재사용 — 신규 hex는 중립 회색 1개뿐.
const PHASE_BAND_FILL: Record<SparklinePhase, string> = {
  full_moon: hexToRgba(DIRECTION_HEX_SIGNED.positive, 0.22),
  waxing: hexToRgba(DIRECTION_HEX_SIGNED.positive, 0.1),
  half_moon: 'rgba(148, 163, 184, 0.14)', // slate-400 — 방향축 대상 아님(비방향 중립)
  waning: hexToRgba(DIRECTION_HEX_SIGNED.negative, 0.1),
  new_moon: hexToRgba(DIRECTION_HEX_SIGNED.negative, 0.22),
}

export function StateBandSparkline({
  series,
  bands,
  transitions = [],
  width = 88,
  height = 28,
  className,
}: StateBandSparklineProps) {
  if (!series || series.length < 2) {
    return (
      <div
        style={{ width, height }}
        className={`rounded bg-gray-100 dark:bg-gray-700 ${className ?? ''}`}
        data-testid="state-band-sparkline-empty"
      />
    )
  }

  // score 정의역은 밴드 min/max 합집합(원칙상 [-1,1]) — bands가 비어도 series로 안전 폴백.
  const domainMin = bands.length
    ? Math.min(...bands.map((b) => b.min))
    : Math.min(...series.map((p) => p.score))
  const domainMax = bands.length
    ? Math.max(...bands.map((b) => b.max))
    : Math.max(...series.map((p) => p.score))
  const domainRange = domainMax - domainMin || 1

  const scoreToY = (score: number) => {
    const clamped = Math.max(domainMin, Math.min(domainMax, score))
    return height - ((clamped - domainMin) / domainRange) * height
  }

  const xForIndex = (index: number) => (index / (series.length - 1)) * width

  const linePoints = series
    .map((p, i) => `${xForIndex(i).toFixed(1)},${scoreToY(p.score).toFixed(1)}`)
    .join(' ')

  const isImproving = series[series.length - 1].score >= series[0].score
  const lineColor = isImproving ? DIRECTION_HEX_SIGNED.positive : DIRECTION_HEX_SIGNED.negative

  const asofIndex = new Map(series.map((p, i) => [p.asof, i]))
  const transitionMarkers = transitions
    .map((t) => asofIndex.get(t))
    .filter((i): i is number => i !== undefined)

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label="상태밴드 스파크라인"
      data-testid="state-band-sparkline"
    >
      {bands.map((band) => {
        const yTop = scoreToY(band.max)
        const yBottom = scoreToY(band.min)
        return (
          <rect
            key={band.phase}
            x={0}
            y={yTop}
            width={width}
            height={Math.max(0, yBottom - yTop)}
            fill={PHASE_BAND_FILL[band.phase]}
            data-testid={`state-band-sparkline-band-${band.phase}`}
          />
        )
      })}

      <polyline
        points={linePoints}
        fill="none"
        stroke={lineColor}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        data-testid="state-band-sparkline-line"
      />

      {transitionMarkers.map((i) => (
        <circle
          key={series[i].asof}
          cx={xForIndex(i)}
          cy={scoreToY(series[i].score)}
          r={1.75}
          fill="#111827"
          stroke="white"
          strokeWidth={0.5}
          data-testid="state-band-sparkline-transition"
        />
      ))}
    </svg>
  )
}
