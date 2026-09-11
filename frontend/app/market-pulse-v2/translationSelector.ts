/**
 * Phase 1.5 S4 — translations envelope → 카드별 sense 셀렉터(얇은 순수 함수).
 *
 * fallback이 정상 경로: translations null / 블록 없음 / 해당 키 없음 / 빈 문자열은 모두 null로
 * 수렴 → 카드는 "밴드만" 렌더(에러·플레이스홀더 없음). meaning.ts(밴드 임계)와 직교.
 */
import type { Translations } from '@/lib/api/marketPulseV2'

export type SenseCardKey = 'regime' | 'breadth' | 'sector' | 'concentration'

export function selectSense(
  translations: Translations | null | undefined,
  cardKey: SenseCardKey,
): string | null {
  const sense = translations?.senses?.[cardKey]
  return sense && sense.trim() ? sense : null
}

/**
 * HUB-V02-S2 (AUTO-1) — 3단 해석: LLM sense → 정적 문장 → null(미렌더).
 * LLM이 있는 날은 selectSense가 이겨 렌더 IDENTICAL(정적은 소비 안 함).
 * LLM이 비고(REFUSED·데이터 부족) 정적 문장이 있으면 그 한 줄을 대신 노출(구멍 봉합).
 * 정적 문장은 호출부가 카드 밴드 데이터로 meaning.ts 함수를 통해 미리 만든 값을 넘긴다
 * (단일소스 = meaning.ts, 여기선 우선순위 결정만). 둘 다 없으면 null → SenseNote 미렌더.
 */
export function resolveSense(
  translations: Translations | null | undefined,
  cardKey: SenseCardKey,
  staticFallback: string | null | undefined,
): string | null {
  return selectSense(translations, cardKey) ?? orNull(staticFallback)
}

/** 빈/공백 문자열은 null로(SenseNote 미렌더 계약과 정합). */
function orNull(s: string | null | undefined): string | null {
  return s && s.trim() ? s : null
}
