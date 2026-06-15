/**
 * MP-UX-S2 — 의미 밴드 카피 단일소스 (director 확정값).
 *
 * Regime 단계 / Anomaly 모드의 "이 값이면 무슨 의미"를 한 곳에 모은다.
 * i18n 짧은 라벨(labels.py)과 달리 문장형 UX 콘텐츠라 FE 상수로 보유(단일 정의, DRY).
 * 임계·색 로직과 무관 — 표시(밴드)용 텍스트 + 단계별 밴드 색만.
 */
import type { AnomalyMode, RegimeId } from '@/lib/api/marketPulseV2'

export const REGIME_MEANING: Record<RegimeId, string> = {
  BULL_EXPANSION: '위험자산 우호 국면. 추세 추종 유리, 광범위 강세.',
  LATE_BULL: '상승은 살아있으나 과열·되돌림 경계. 신규 진입 신중, 보유 점검.',
  TRANSITION: '방향 불확실·신호 혼재. 포지션 축소·관망 우위.',
  BEAR_CONTRACTION: '위험회피 우세, 신용 경색 조짐. 방어적 포지션.',
  CRISIS: '시스템 스트레스. 현금·안전자산 비중, 급변동 대비.',
}

/** 단계별 밴드 색 (신규 표시 — 기존 카드 색 로직과 무관). good→bad 순. */
export const REGIME_TONE: Record<RegimeId, string> = {
  BULL_EXPANSION: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  LATE_BULL: 'bg-amber-50 text-amber-800 border-amber-200',
  TRANSITION: 'bg-slate-50 text-slate-700 border-slate-200',
  BEAR_CONTRACTION: 'bg-orange-50 text-orange-800 border-orange-200',
  CRISIS: 'bg-rose-50 text-rose-800 border-rose-200',
}

export const MODE_MEANING: Record<AnomalyMode, string> = {
  CALM: '이상 신호 없음. 평상 범위.',
  HYBRID: '1개 신호 발동. 부분 경계.',
  ANOMALY: '2개 이상 동시 발동. 강한 경계.',
}
