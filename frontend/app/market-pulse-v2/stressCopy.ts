/**
 * MPS-2 — 스트레스 카드 결정론 카피 템플릿 (순수 함수, LLM·외부 0).
 *
 * 소속: market-pulse-v2 (FE 카피 단일소스).
 * 계약(D-MPS-COPY): 백엔드 state enum만 조합 — FE에서 새 임계값·판정 생성 금지.
 *   금지규칙 2: ① 유사성 어휘("위기 유사/닮음") 금지(유사=analog 카드 소관) ② 단계명
 *   "위기/CRISIS/crisis" 금지(백엔드 밴드 enum = severe, D-MPS-BAND-NAME). 이 파일의 전
 *   산출 문구는 stress_copy.test.tsx가 전수 스캔으로 금지 어휘 부재를 고정한다(백엔드
 *   test_band_vocab_excludes_crisis의 FE 짝).
 * F2(D-MPS-COPY): percentile.value = from-below(≤ 비율). 상위 N% = 100 − value.
 */

export type LevelBand = 'stable' | 'caution' | 'severe'
export type StressState = 'worsening' | 'easing' | 'mixed'
export type PriceState = 'uptrend' | 'downtrend' | 'mixed'

export interface StressCopyInput {
  levelBand: LevelBand
  percentileValue: number
  stressState: StressState
  priceState: PriceState
}

export interface StressCopy {
  level: string
  percentile: string
  direction: string
  divergence: boolean // 가격 상승 ∧ 스트레스 악화 = 최고가치(D-MPS-DIRECTION)
  reverseDivergence: boolean // 가격 하락 ∧ 스트레스 완화
}

/** 상위 N%(더 스트레스 높은 쪽) = 100 − value(from-below). round 1. */
export function topPercent(value: number): number {
  return Math.round((100 - value) * 10) / 10
}

const LEVEL_PHRASE: Record<LevelBand, string> = {
  stable: '스트레스 낮은 구간',
  caution: '스트레스 주의 구간',
  severe: '스트레스 심화 구간', // "위기" 금지(D-MPS-BAND-NAME)
}

const STRESS_PHRASE: Record<StressState, string> = {
  worsening: '스트레스 악화',
  easing: '스트레스 완화',
  mixed: '스트레스 혼조',
}

const PRICE_PHRASE: Record<PriceState, string> = {
  uptrend: '가격 상승',
  downtrend: '가격 하락',
  mixed: '가격 혼조',
}

/** 백분위 문구: caution/severe = "지난 3년 중 상위 N%" 강조 / stable = 중립(상위% 미생성). */
function percentilePhrase(band: LevelBand, value: number): string {
  if (band === 'stable') {
    return '지난 3년 대비 낮은 수준'
  }
  return `지난 3년 중 상위 ${topPercent(value)}%`
}

/** 방향 9조합: stress·price 양쪽 언급 + 괴리/역괴리 구분. */
function directionPhrase(
  stressState: StressState,
  priceState: PriceState,
): { text: string; divergence: boolean; reverseDivergence: boolean } {
  const base = `${STRESS_PHRASE[stressState]} · ${PRICE_PHRASE[priceState]}`
  const divergence = priceState === 'uptrend' && stressState === 'worsening'
  const reverseDivergence = priceState === 'downtrend' && stressState === 'easing'
  if (divergence) {
    return { text: `${base} — 괴리 주시`, divergence: true, reverseDivergence: false }
  }
  if (reverseDivergence) {
    return { text: `${base} — 역괴리`, divergence: false, reverseDivergence: true }
  }
  return { text: base, divergence: false, reverseDivergence: false }
}

export function buildStressCopy(input: StressCopyInput): StressCopy {
  const dir = directionPhrase(input.stressState, input.priceState)
  return {
    level: LEVEL_PHRASE[input.levelBand],
    percentile: percentilePhrase(input.levelBand, input.percentileValue),
    direction: dir.text,
    divergence: dir.divergence,
    reverseDivergence: dir.reverseDivergence,
  }
}
