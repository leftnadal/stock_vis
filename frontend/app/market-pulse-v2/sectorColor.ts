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

/* ───────────────────────── MP2-SECTOR-CD Slice 1 ─────────────────────────
 * cd_state 4-상태 색 토큰 (단일소스). BE `classify_cd_state`가 서빙한 문자열을
 * 키로 매핑만 — FE 재분류 0. 유보(null)는 중성 회색.
 * 상승축(주도·강화)=rose, 하락축(부진·악화)=sky로 기존 한국 관례와 정합.
 * 중간 상태는 주황(둔화)·청록(개선)으로 분리.
 */

export type CdState =
  | 'leading_strengthening' // 주도·강화
  | 'leading_weakening' // 주도·둔화
  | 'lagging_improving' // 부진·개선
  | 'lagging_deteriorating' // 부진·악화

interface CdToken {
  label: string
  badge: string // 뱃지 Tailwind (bg/text/border)
  dot: string // 사분면 점 hex
}

const CD_TOKENS: Record<CdState, CdToken> = {
  leading_strengthening: {
    label: '주도·강화',
    badge: 'bg-rose-100 text-rose-800 border-rose-200',
    dot: '#f43f5e', // rose-500
  },
  leading_weakening: {
    label: '주도·둔화',
    badge: 'bg-amber-100 text-amber-800 border-amber-200',
    dot: '#f59e0b', // amber-500
  },
  lagging_improving: {
    label: '부진·개선',
    badge: 'bg-teal-100 text-teal-800 border-teal-200',
    dot: '#14b8a6', // teal-500
  },
  lagging_deteriorating: {
    label: '부진·악화',
    badge: 'bg-sky-100 text-sky-800 border-sky-200',
    dot: '#0ea5e9', // sky-500
  },
}

// 유보(null) 중성 토큰.
const CD_RESERVED_TOKEN: CdToken = {
  label: '판단 유보',
  badge: 'bg-slate-100 text-slate-500 border-slate-200',
  dot: '#cbd5e1', // slate-300 (미표시 대비 폴백; 점은 렌더 안 함)
}

/** cd_state → 한글 짧은 라벨(유보 포함). */
export function cdStateLabel(state: CdState | null): string {
  if (state == null) return CD_RESERVED_TOKEN.label
  return CD_TOKENS[state].label
}

/** cd_state → 뱃지 Tailwind 클래스(유보 포함). */
export function cdStateBadgeClass(state: CdState | null): string {
  if (state == null) return CD_RESERVED_TOKEN.badge
  return CD_TOKENS[state].badge
}

/** cd_state → 사분면 점 hex. 유보는 점 미표시가 원칙이나 폴백값 제공. */
export function cdStateDotFill(state: CdState | null): string {
  if (state == null) return CD_RESERVED_TOKEN.dot
  return CD_TOKENS[state].dot
}

/**
 * "전환 확인 중" 판정 — 서빙된 공식(cd_state)과 원시(cd_state_raw)가 서로 다름.
 * CD-TRANSITION-INDICATOR(CD-READ). **재분류 아님**: 좌표·값 기반 분류 로직 신설 0,
 *   두 서빙값의 단순 비교뿐(규칙 #1). 어느 하나 null이면 false(비교 불가 → 표시 안 함).
 */
export function isTransitioning(
  cd_state: CdState | null | undefined,
  cd_state_raw: CdState | null | undefined,
): boolean {
  return cd_state != null && cd_state_raw != null && cd_state !== cd_state_raw
}

/** 전환 확인 중 강조색(주황 계열) — 점선 링·칩 단일소스. cd 상태색과 구분되는 중성 신호색. */
export const CD_TRANSITION_HEX = '#f97316' // orange-500

/** 범례용 4상태 순서(유보 제외). */
export const CD_STATE_ORDER: CdState[] = [
  'leading_strengthening',
  'leading_weakening',
  'lagging_improving',
  'lagging_deteriorating',
]
