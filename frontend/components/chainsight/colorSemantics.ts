/**
 * chainsight 구획 방향성 색 시맨틱 단일소스 — 한국축(DECISIONS D-COLOR-SYSTEM).
 *
 *   상승 · 매수 · 긍정(강화) = rose(빨강)
 *   하락 · 매도 · 부정(약화) = sky(파랑)
 *
 * 색상값은 dashboard `components/eod/colorSemantics.ts` 및
 * `app/market-pulse-v2/sectorColor.ts`와 정합(rose #f43f5e / sky #0ea5e9).
 * eod 파일은 타 구획이므로 import하지 않고, 같은 시맨틱 구성을 이 구획 로컬로 둔다.
 *
 * chainsight 컴포넌트는 방향성 색을 하드코딩하지 않고 이 파일을 소비한다(구획 내 drift 방지).
 *
 * ⚠ 색 단독 인코딩 금지 — 소비처는 ▲▼·±·화살표 아이콘을 항상 병기(색은 보조, 색맹 안전).
 * ⚠ Tailwind 정적 클래스만(퍼지 안전) — 동적 클래스명 생성 금지, 전체 리터럴만 사용.
 * ⚠ 비방향 색(에러·데이터 신선도·관계강도 등급·sector/relation 카테고리)은 이 축 대상 아님(무변경).
 */

// 한국축 톤 리터럴 (sectorColor / eod 정합) — 각 리터럴이 소스에 그대로 존재(퍼지 안전)
const ROSE_TEXT = 'text-rose-600 dark:text-rose-400';
const SKY_TEXT = 'text-sky-600 dark:text-sky-400';

/** 등락(가격 변화율) 텍스트 색 — 상승 rose / 하락 sky */
export const CHANGE_TEXT = {
  up: ROSE_TEXT,
  down: SKY_TEXT,
} as const;

/** 긍정/부정(signed 지표·관계 강화/약화) 텍스트 색 — 긍정 rose / 부정 sky */
export const STRENGTH_TEXT = {
  positive: ROSE_TEXT,
  negative: SKY_TEXT,
} as const;

/** signed 지표 바 채움(양방향) — 양수(긍정) rose / 음수(부정) sky */
export const SIGNED_BAR = {
  positive: 'bg-rose-500',
  negative: 'bg-sky-500',
} as const;
