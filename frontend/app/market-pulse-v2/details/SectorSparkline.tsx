'use client'

import type { SectorHistory } from '@/lib/api/marketPulseV2'
import { sectorFlow } from '../meaning'
import { sparkPoints } from './ConcentrationSparkline'
import { sectorDivergingDir } from '../sectorColor'

const W = 88
const H = 24
const PAD = 2

/**
 * rel_strength 방향(sectorColor.ts 단일소스) → 폴리라인/마지막점 색.
 * 한국 관례: 상승=rose, 하락=sky.
 * meaning.ts sectorFlow는 방향 판정에 재사용(dir 추출)하되, 색은 새 유틸 경유.
 */
const STROKE: Record<string, string> = {
  up: 'text-rose-500',
  down: 'text-sky-500',
  flat: 'text-slate-400',
}
const FILL: Record<string, string> = {
  up: 'fill-rose-600',
  down: 'fill-sky-600',
  flat: 'fill-slate-500',
}

/** sectorFlow dir('in'|'out'|'flat') → sectorColor dir('up'|'down'|'flat') 변환. */
function flowToColorDir(flowDir: string): 'up' | 'down' | 'flat' {
  if (flowDir === 'in') return 'up'
  if (flowDir === 'out') return 'down'
  return 'flat'
}

/**
 * MP-UX-S5-B — 단일 섹터 rel_strength 인라인 스파크라인 (sector_history 데이터원).
 * sparkPoints 재사용(가짜 0패딩 없음). 색=sectorColor.ts(한국 관례: 상승=rose/하락=sky).
 * 빈 history → "—" graceful(합성 0). 일수 가변(≤30, 29 하드코딩 없음).
 * rel_strength=0 기준선은 0이 [min,max] 범위 안일 때만(합성 0 금지).
 */
export function SectorSparkline({ entry }: { entry: SectorHistory }) {
  const values = entry.history.map((p) => p.rel_strength)
  if (values.length === 0) {
    return (
      <span className="text-xs text-slate-300" aria-label={`${entry.symbol} 이력 없음`}>
        —
      </span>
    )
  }

  const points = sparkPoints(values, W, H, PAD)
  const last = values[values.length - 1]
  // sectorFlow로 방향 판정 → flowToColorDir로 색 방향 변환 → STROKE/FILL 색 적용
  const flowDir = sectorFlow(last).dir
  const colorDir = flowToColorDir(flowDir)
  const single = values.length < 2

  // sparkPoints와 동일 정규화 — 마지막점/기준선 좌표 산출
  const finite = values.filter((v) => Number.isFinite(v))
  const min = Math.min(...finite)
  const max = Math.max(...finite)
  const span = max - min || 1
  const lastX = single ? W / 2 : W - PAD
  const lastY = PAD + (H - PAD * 2) * (1 - (last - min) / span)

  const zeroInRange = min <= 0 && max >= 0
  const zeroY = PAD + (H - PAD * 2) * (1 - (0 - min) / span)

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width={W}
      height={H}
      role="img"
      aria-label={`${entry.symbol} 상대강도 스파크라인, 최근 ${values.length}일`}
      preserveAspectRatio="none"
    >
      {zeroInRange ? (
        <line
          x1={0}
          y1={zeroY}
          x2={W}
          y2={zeroY}
          stroke="currentColor"
          className="text-slate-200"
          strokeWidth={0.75}
          strokeDasharray="2 2"
        />
      ) : null}
      {!single ? (
        <polyline
          points={points}
          fill="none"
          stroke="currentColor"
          className={STROKE[colorDir]}
          strokeWidth={1.25}
        />
      ) : null}
      <circle cx={lastX} cy={lastY} r={2} className={FILL[colorDir]} />
    </svg>
  )
}
