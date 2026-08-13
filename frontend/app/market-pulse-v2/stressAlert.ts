/**
 * MPS-2 — 스트레스 경보 색 단일소스 (D-MPS-COLOR 안 1: 경보 프레임).
 *
 * 소속: market-pulse-v2 (StressCard 색 단일소스 — 카드 내 색 하드코딩 금지).
 * 규약: 스트레스 = 경보 가족(anomaly와 동일 축). stable=slate(무채)/caution=amber/severe=rose.
 *   가격 행은 무채색(sectorColor 미적용 — rose=상승 규약은 등락률 표면에서만 유지, 색 충돌 회피).
 *   easing(완화)은 무채·low-key만 — 긍정색(sky 등) 도입 금지.
 * cf. TASKQUEUE COLOR-TOKEN-UNIFY(AnomalyPanel rose→이 토큰 통일, 휴면).
 */
import type { StressLevelBand, StressDirState } from '@/lib/api/marketPulseV2'

// 밴드 뱃지: 배경+테두리+텍스트 (경보 강도 = slate→amber→rose).
const BAND_BADGE: Record<StressLevelBand, string> = {
  stable: 'border-slate-200 bg-slate-50 text-slate-600',
  caution: 'border-amber-300 bg-amber-50 text-amber-700',
  severe: 'border-rose-300 bg-rose-50 text-rose-700',
}

// 밴드 표시어(display term) — "위기" 금지(D-MPS-BAND-NAME). severe = "심화".
const BAND_LABEL: Record<StressLevelBand, string> = {
  stable: '안정',
  caution: '주의',
  severe: '심화',
}

export function stressBandBadgeClass(band: StressLevelBand): string {
  return BAND_BADGE[band]
}

export function stressBandLabel(band: StressLevelBand): string {
  return BAND_LABEL[band]
}

// 스트레스 방향 텍스트색: 악화=경보(rose), 완화·혼조=무채(low-key). 긍정색 없음.
export function stressStateTextClass(state: StressDirState): string {
  return state === 'worsening' ? 'text-rose-700' : 'text-slate-500'
}

// 괴리 강조 배지 = 경보(rose). 최고가치 정보(D-MPS-DIRECTION).
export function divergenceBadgeClass(): string {
  return 'border-rose-300 bg-rose-50 text-rose-700'
}

// 가격 행 = 무채색(sectorColor 미적용).
export function priceNeutralTextClass(): string {
  return 'text-slate-500'
}
