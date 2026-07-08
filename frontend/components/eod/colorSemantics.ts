/**
 * dashboard(eod) 구획 방향성 색 시맨틱 단일소스 — 한국축(DECISIONS D-COLOR-SYSTEM).
 *
 *   상승 · 매수 · 강세(긍정) = rose(빨강)
 *   하락 · 매도 · 약세(부정) = sky(파랑)
 *
 * 색상값은 `app/market-pulse-v2/sectorColor.ts`와 정합(rose #f43f5e / sky #0ea5e9).
 * eod 구획 컴포넌트는 방향성 색을 하드코딩하지 않고 이 파일을 소비한다(구획 내 drift 방지).
 *
 * ⚠ 색 단독 인코딩 금지 — 소비처는 라벨/아이콘/부호를 항상 병기(색은 보조, 색맹 안전).
 * ⚠ Tailwind 정적 클래스만(퍼지 안전) — 동적 클래스명 생성 금지, 전체 리터럴만 사용.
 * ⚠ 비방향 색(데이터 신선도·변동성 레짐·리스크 경고)은 이 축 대상 아님(무변경).
 */

// 한국축 톤 리터럴 (sectorColor 정합) — 각 리터럴이 소스에 그대로 존재(퍼지 안전)
const ROSE_TEXT = 'text-rose-600 dark:text-rose-400';
const SKY_TEXT = 'text-sky-600 dark:text-sky-400';

/** 등락(가격 변화율) 텍스트 색 — 상승 rose / 하락 sky */
export const CHANGE_TEXT = {
  up: ROSE_TEXT,
  down: SKY_TEXT,
} as const;

/** 지수 등락 칩 (bg + text) — 상승 rose / 하락 sky / 보합 gray */
export const CHANGE_CHIP = {
  up: 'bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300',
  down: 'bg-sky-50 dark:bg-sky-900/20 text-sky-700 dark:text-sky-300',
  neutral: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300',
} as const;

/** 강세/약세 카운트 텍스트 — 강세(긍정) rose / 약세(부정) sky */
export const STRENGTH_TEXT = {
  positive: ROSE_TEXT,
  negative: SKY_TEXT,
} as const;

/** 강세 비율 바 채움 색 (긍정 방향) */
export const STRENGTH_BAR_FILL = 'bg-rose-500';

/** 방향 배지(매수/매도) bg + text — 매수 rose / 매도 sky */
export const DIRECTION_BADGE = {
  buy: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  sell: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300',
} as const;

/** 방향 강도 spine 채움 — 매수 rose / 매도 sky */
export const DIRECTION_SPINE = {
  buy: 'bg-rose-500',
  sell: 'bg-sky-500',
} as const;

/** 확신 강도 도트(방향 5단계) — 매수측 rose / 중립 gray / 매도측 sky */
export const CONFIDENCE_DOT = {
  buyStrong: 'bg-rose-500',
  buy: 'bg-rose-400',
  neutral: 'bg-gray-400',
  sell: 'bg-sky-400',
  sellStrong: 'bg-sky-500',
} as const;

/** SVG/차트 stroke·fill hex (MiniSparkline 등) — 상승 rose-500 / 하락 sky-500 */
export const DIRECTION_HEX = {
  up: '#f43f5e', // rose-500
  down: '#0ea5e9', // sky-500
} as const;

/** SVG 영역 채움 rgba (hex와 동일 톤 @ 0.1) */
export const DIRECTION_FILL_RGBA = {
  up: 'rgba(244,63,94,0.1)', // rose-500
  down: 'rgba(14,165,233,0.1)', // sky-500
} as const;
