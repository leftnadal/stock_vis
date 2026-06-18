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
