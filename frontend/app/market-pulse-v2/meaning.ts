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

// MP-UX-S4: 단계 심각도 순서 (rules.yaml 오름차순). 전환 방향(개선/악화) 판정 단일소스.
export const STAGE_ORDER: Record<RegimeId, number> = {
  BULL_EXPANSION: 0,
  LATE_BULL: 1,
  TRANSITION: 2,
  BEAR_CONTRACTION: 3,
  CRISIS: 4,
}

// MP-UX-S4: 전환 방향 문구 토큰 (자유 텍스트 컴포넌트 산재 금지).
export const TRANSITION_DIR = { improve: '상향(개선)', worsen: '하향(악화)' } as const

// MP-UX-S4: 미지 enum graceful — 색/순서 미정의 시 fallback (crash 0, hex 하드코딩 금지).
export const REGIME_NEUTRAL_TONE = 'bg-slate-100 text-slate-600 border-slate-200'

export function regimeTone(stage: string): string {
  return (REGIME_TONE as Record<string, string>)[stage] ?? REGIME_NEUTRAL_TONE
}

export function stageOrder(stage: string): number | null {
  return Object.prototype.hasOwnProperty.call(STAGE_ORDER, stage)
    ? (STAGE_ORDER as Record<string, number>)[stage]
    : null
}

// MP-UX-TITLE-SOURCE(C): "레짐/국면" 표시 용어 단일소스 — '국면'으로 통일.
// 컴포넌트 산재 문자열을 이 상수 참조로 치환(로직·enum 불변, 표시만).
export const REGIME_TERM = '국면'

// ─────────────────────────────────────────────────────────────
// MP-UX-S5 — 자금흐름(Concentration·Sector) 의미밴드 단일소스.
// 원시 기술용어(top10_weight·HHI·rel_strength)를 "한 줄 의미 + 색 위치"로.
// 색·임계·문구·순서 전부 여기 한 곳. 컴포넌트엔 hex·임계·문구 산재 0.
// ─────────────────────────────────────────────────────────────

/** 자금흐름 강도 톤 (calm→hot 순, hex 0 — tailwind 토큰 재사용). */
export const FLOW_TONE = {
  calm: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  mild: 'bg-sky-50 text-sky-800 border-sky-200',
  warn: 'bg-amber-50 text-amber-800 border-amber-200',
  hot: 'bg-rose-50 text-rose-800 border-rose-200',
} as const

/** 미지/범위이탈 graceful fallback (crash 0). */
export const FLOW_NEUTRAL_TONE = 'bg-slate-100 text-slate-600 border-slate-200'

// 집중도 의미밴드 임계값 — top10_weight 기준(0~1).
//   0.40 = anomaly rules.yaml R02 "집중도 극단" 경보선(grounded 단일 앵커).
//   0.30 / 0.35 = TUNE(분산↔약한↔중간 구간 분할, 실데이터 분포로 보정 권고).
// ⚠️ 지시서 pseudocode는 hhi+DOJ(0.15/.20/.25)를 제안했으나, STEP 0 실측상
//    HHI=Σweight²로 SPY 실제값 0.02~0.06 스케일 → 항상 "분산"으로 읽혀 무용.
//    시스템이 집중도 신호로 실제 쓰는 top10_weight로 전환(grounded ground truth).
export const CONCENTRATION_THRESHOLDS = { dispersed: 0.3, weak: 0.35, mid: 0.4 } as const // TUNE(0.40만 grounded)

export type FlowBandKey = 'dispersed' | 'weak' | 'mid' | 'strong'

export interface FlowBand {
  index: number // 0..3 (낮을수록 분산)
  key: FlowBandKey
  label: string
  tone: string
}

/** 집중도 4밴드(분산→강한쏠림) — 밴드 UI(● 현 위치) 렌더 단일소스. */
export const CONCENTRATION_SCALE: FlowBand[] = [
  { index: 0, key: 'dispersed', label: '분산', tone: FLOW_TONE.calm },
  { index: 1, key: 'weak', label: '약한 쏠림', tone: FLOW_TONE.mild },
  { index: 2, key: 'mid', label: '중간 쏠림', tone: FLOW_TONE.warn },
  { index: 3, key: 'strong', label: '강한 쏠림', tone: FLOW_TONE.hot },
]

/** top10_weight → 밴드. null/비유한 → null(대기·미렌더, 0 변환 금지). */
export function concentrationBand(top10Weight: number | null | undefined): FlowBand | null {
  if (top10Weight == null || !Number.isFinite(top10Weight)) return null
  const t = CONCENTRATION_THRESHOLDS
  if (top10Weight < t.dispersed) return CONCENTRATION_SCALE[0]
  if (top10Weight < t.weak) return CONCENTRATION_SCALE[1]
  if (top10Weight < t.mid) return CONCENTRATION_SCALE[2]
  return CONCENTRATION_SCALE[3]
}

const CONCENTRATION_PHRASE: Record<FlowBandKey, string> = {
  dispersed: '자금이 고르게 분산',
  weak: '약한 집중',
  mid: '소수 대형주로 모이는 중',
  strong: '소수 대형주에 강하게 쏠림',
}

/** 밴드 + (선택)추세 방향 → 한 줄 문장. 추세 없으면 괄호 생략. */
export function concentrationSentence(band: FlowBand, trendDir?: string | null): string {
  const base = CONCENTRATION_PHRASE[band.key]
  return trendDir ? `${base}(최근 ${trendDir})` : base
}

export type SectorDir = 'in' | 'out' | 'flat'

/** rel_strength 부호 → 유입/유출/중립. epsilon(% 단위) 안쪽은 flat. */
export function sectorFlow(
  value: number | null | undefined,
  epsilon = 0.1,
): { dir: SectorDir; tone: string } {
  if (value == null || !Number.isFinite(value)) return { dir: 'flat', tone: FLOW_NEUTRAL_TONE }
  if (value > epsilon) return { dir: 'in', tone: FLOW_TONE.calm } // 유입=상대강세
  if (value < -epsilon) return { dir: 'out', tone: FLOW_TONE.hot } // 유출=상대약세
  return { dir: 'flat', tone: FLOW_NEUTRAL_TONE }
}

/**
 * 유입(리더)·유출(후행) KO 라벨 → 한 줄. 빈/누락 입력은 해당 쪽 생략.
 * 양쪽 다 비면 null(문장 자체 생략 = 대기, 합성 0).
 * 라벨 번역은 호출부(카드)에서 끝낸 값을 받는다(meaning.ts는 i18n-무관).
 */
export function sectorSentence(inNames: string[], outNames: string[]): string | null {
  const parts: string[] = []
  if (inNames.length) parts.push(`${inNames.join('·')}로 유입`)
  if (outNames.length) parts.push(`${outNames.join('·')}서 유출`)
  return parts.length ? parts.join(', ') : null
}

export type TrendDir = 'up' | 'down' | 'flat'

// MP-UX-S5 Part B: 집중도 추세 방향 문구(스파크라인 주석 단일소스). arrow는 sentence 괄호용.
export const CONCENTRATION_TREND: Record<TrendDir, { arrow: string; label: string }> = {
  up: { arrow: '↑', label: '쏠림 심화' },
  down: { arrow: '↓', label: '분산' },
  flat: { arrow: '→', label: '유지' },
}

/** top10 시계열 추세 → 방향(마지막 vs 처음, epsilon 안쪽은 flat). 2점 미만 → null. */
export function concentrationTrend(values: number[], epsilon = 0.01): TrendDir | null {
  const clean = values.filter((v) => Number.isFinite(v))
  if (clean.length < 2) return null
  const delta = clean[clean.length - 1] - clean[0]
  if (delta > epsilon) return 'up'
  if (delta < -epsilon) return 'down'
  return 'flat'
}
