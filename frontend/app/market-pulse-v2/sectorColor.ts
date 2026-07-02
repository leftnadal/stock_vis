/**
 * sector 표면 색 단일소스 — 한국 관례(상승=rose/빨강, 하락=sky/파랑).
 *
 * 4개 sector 표면(SectorHeatmap·SectorDetail·SectorSparkline·SectorCardSummary)이
 * 모두 이 파일에서 색 결정 → 표면 간 drift 방지.
 *
 * ⚠ rotation_index 절대 사용 금지 — 11섹터 동일값으로 전 타일 동색 버그.
 *   색은 오직 per-섹터 rel_strength 기반 sectorDivergingDir 경유.
 * ⚠ meaning.ts의 sectorFlow·FLOW_TONE·FLOW_NEUTRAL_TONE 수정 금지
 *   (breadth/concentration 공유). sector 컴포넌트는 이 파일로 우회.
 */

export type SectorColorDir = 'up' | 'down' | 'flat'

/**
 * rel_strength 수치 → 색 방향 판정.
 * v > epsilon → 'up'(상승/유입), v < -epsilon → 'down'(하락/유출), else → 'flat'.
 * epsilon 기본값 0.1(sectorFlow 관례 동일).
 */
export function sectorDivergingDir(v: number, epsilon = 0.1): SectorColorDir {
  if (v > epsilon) return 'up'
  if (v < -epsilon) return 'down'
  return 'flat'
}

/**
 * 히트맵 타일 Tailwind 클래스 (bg/text/border).
 * up=rose(|v|>0.4 진한 bg-rose-300 / else bg-rose-100),
 * down=sky(진한 bg-sky-300 / else bg-sky-100),
 * flat=bg-slate-100.
 * 기존 SectorHeatmap heatTileClass 로직 그대로 이관 — 동작 동일.
 */
export function sectorTileClass(v: number, epsilon = 0.1): string {
  const dir = sectorDivergingDir(v, epsilon)
  if (dir === 'up') {
    return Math.abs(v) > 0.4
      ? 'bg-rose-300 text-rose-900 border-rose-400'
      : 'bg-rose-100 text-rose-800 border-rose-200'
  }
  if (dir === 'down') {
    return Math.abs(v) > 0.4
      ? 'bg-sky-300 text-sky-900 border-sky-400'
      : 'bg-sky-100 text-sky-800 border-sky-200'
  }
  return 'bg-slate-100 text-slate-600 border-slate-200'
}

/**
 * 텍스트 색 Tailwind 클래스.
 * up=text-rose-600, down=text-sky-600, flat=text-slate-400.
 */
export function sectorTextClass(v: number, epsilon = 0.1): string {
  const dir = sectorDivergingDir(v, epsilon)
  if (dir === 'up') return 'text-rose-600'
  if (dir === 'down') return 'text-sky-600'
  return 'text-slate-400'
}

/**
 * Recharts Cell fill hex.
 * up='#f43f5e'(rose-500), down='#0ea5e9'(sky-500), flat='#94a3b8'(slate-400).
 */
export function sectorBarFill(v: number, epsilon = 0.1): string {
  const dir = sectorDivergingDir(v, epsilon)
  if (dir === 'up') return '#f43f5e'
  if (dir === 'down') return '#0ea5e9'
  return '#94a3b8'
}
