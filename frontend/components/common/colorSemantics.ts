/**
 * 앱 공용 방향성 색 시맨틱 토큰 — 한국축 단일소스 (DECISIONS D-COLOR-SYSTEM · D-COLOR-TOKEN).
 *
 *   상승 · 매수 · 강세 · 유입 · 긍정 = rose(빨강, #f43f5e)
 *   하락 · 매도 · 약세 · 유출 · 부정 = sky(파랑, #0ea5e9)
 *   중립 = slate/gray
 *
 * 3벌 로컬 시맨틱(eod · market-pulse-v2 · chainsight)의 합집합 승격분. 값·shape는
 * 원본 3벌과 IDENTICAL(회수 슬라이스 TOKEN-RECLAIM의 입력). 소비자 0 — export만(순수 신설).
 *
 * 축 분류(export 접두/이름):
 *   - CHANGE_…        = 등락 축(up/down) — 가격 변화율 등
 *   - STRENGTH_… · SIGNED_… · DIRECTION_BAND · DIRECTION_TEXT_… = 긍정부정 축(positive/negative)
 *   - DIRECTION_BADGE · DIRECTION_SPINE · CONFIDENCE_DOT        = 매매 축(buy/sell)
 *   - DIRECTION_HEX_CHANGE(up/down) vs DIRECTION_HEX_SIGNED(positive/negative)
 *     = same-name·different-shape 충돌 회피 위해 축별 분리(D-COLOR-TOKEN-AMEND-1 후보).
 *       `DIRECTION_HEX`라는 이름은 두지 않는다(축 혼동·오용 차단).
 *
 * ⚠ 색 단독 인코딩 금지 — 소비처는 라벨/아이콘/부호를 항상 병기(색은 보조, 색맹 안전).
 * ⚠ Tailwind 정적 리터럴만(퍼지 안전) — 동적 클래스명 생성 금지, 전체 리터럴만 사용.
 * ⚠ 비방향 색(데이터 신선도·변동성/쏠림 강도 FLOW_TONE·경고·카테고리 팔레트)은 이 축 대상 아님.
 */

// 한국축 톤 리터럴 (rose-600/sky-600 텍스트, dark 변형 포함) — 각 리터럴 소스에 그대로 존재.
const ROSE_TEXT = 'text-rose-600 dark:text-rose-400';
const SKY_TEXT = 'text-sky-600 dark:text-sky-400';

// ─────────────────────────────────────────────────────────────────────────────
// 등락 축(up/down)
// ─────────────────────────────────────────────────────────────────────────────

/** 등락(가격 변화율) 텍스트 색 — 상승 rose / 하락 sky. (eod≡chainsight IDENTICAL) */
export const CHANGE_TEXT = {
  up: ROSE_TEXT,
  down: SKY_TEXT,
} as const;

/** 지수 등락 칩 (bg + text) — 상승 rose / 하락 sky / 보합 gray. (eod) */
export const CHANGE_CHIP = {
  up: 'bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300',
  down: 'bg-sky-50 dark:bg-sky-900/20 text-sky-700 dark:text-sky-300',
  neutral: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300',
} as const;

/** SVG/차트 stroke·fill hex — 등락 축(상승 rose-500 / 하락 sky-500). (eod DIRECTION_HEX 개명) */
export const DIRECTION_HEX_CHANGE = {
  up: '#f43f5e', // rose-500
  down: '#0ea5e9', // sky-500
} as const;

/** SVG 영역 채움 rgba (등락 hex와 동일 톤 @ 0.1). (eod) */
export const DIRECTION_FILL_RGBA = {
  up: 'rgba(244,63,94,0.1)', // rose-500
  down: 'rgba(14,165,233,0.1)', // sky-500
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 긍정부정 축(positive/negative)
// ─────────────────────────────────────────────────────────────────────────────

/** 강세/약세 카운트 텍스트 — 강세(긍정) rose / 약세(부정) sky. (eod≡chainsight IDENTICAL) */
export const STRENGTH_TEXT = {
  positive: ROSE_TEXT,
  negative: SKY_TEXT,
} as const;

/** 강세 비율 바 채움 색(긍정 방향). (eod) */
export const STRENGTH_BAR_FILL = 'bg-rose-500';

/** signed 지표 바 채움(양방향) — 양수(긍정) rose / 음수(부정) sky. (chainsight) */
export const SIGNED_BAR = {
  positive: 'bg-rose-500',
  negative: 'bg-sky-500',
} as const;

/** 방향 의미 밴드(bg+text+border) — regime/breadth/flow 의미밴드. (market-pulse) */
export const DIRECTION_BAND = {
  positive: 'bg-rose-50 text-rose-800 border-rose-200',
  negative: 'bg-sky-50 text-sky-800 border-sky-200',
  neutral: 'bg-slate-50 text-slate-700 border-slate-200',
} as const;

/** 방향 텍스트 색(긍정부정, dark 변형 없음) — 상승/강세 rose / 하락/약세 sky. (market-pulse) */
export const DIRECTION_TEXT = {
  positive: 'text-rose-600',
  negative: 'text-sky-600',
} as const;

/** 보조 통계(신고가/신저가 등) 약한 강조 텍스트 색. (market-pulse) */
export const DIRECTION_TEXT_SOFT = {
  positive: 'text-rose-500',
  negative: 'text-sky-500',
} as const;

/** SVG/차트 stroke·fill hex — 긍정부정 축(긍정 rose-500 / 부정 sky-500). (market-pulse DIRECTION_HEX 개명) */
export const DIRECTION_HEX_SIGNED = {
  positive: '#f43f5e', // rose-500
  negative: '#0ea5e9', // sky-500
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// 매매 축(buy/sell) + 확신 강도
// ─────────────────────────────────────────────────────────────────────────────

/** 방향 배지(매수/매도) bg + text — 매수 rose / 매도 sky. (eod) */
export const DIRECTION_BADGE = {
  buy: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  sell: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300',
} as const;

/** 방향 강도 spine 채움 — 매수 rose / 매도 sky. (eod) */
export const DIRECTION_SPINE = {
  buy: 'bg-rose-500',
  sell: 'bg-sky-500',
} as const;

/** 확신 강도 도트(방향 5단계) — 매수측 rose / 중립 gray / 매도측 sky. (eod) */
export const CONFIDENCE_DOT = {
  buyStrong: 'bg-rose-500',
  buy: 'bg-rose-400',
  neutral: 'bg-gray-400',
  sell: 'bg-sky-400',
  sellStrong: 'bg-sky-500',
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// grade 축(상태등급 gray/yellow/orange/red) — ⚠ 방향색(rose/sky) 아님, 강도/경고 축.
// ─────────────────────────────────────────────────────────────────────────────
// credit_signals 상태등급 + TH 히트 밴드 등 "등급 강도"를 표현하는 비방향 색.
// gray는 저채도로 눌러(낮은 대비) 비-gray(yellow→orange→red)가 자연 부상하도록 설계.
// 로컬 grade 색 정의 금지 — 소비처는 이 토큰만 소비(D-COLOR-TOKEN 단일소스 원칙).

/** 상태등급 리터럴 유니온 (credit_signals grade + 재사용). */
export type Grade = 'gray' | 'yellow' | 'orange' | 'red';

/** grade 칩(bg + text + border) — gray 저채도, yellow/orange/red 상향 강조. (Tailwind 정적 리터럴) */
export const GRADE_CHIP = {
  gray: 'bg-gray-50 text-gray-400 border-gray-200 dark:bg-gray-800/40 dark:text-gray-500 dark:border-gray-700',
  yellow: 'bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-900/25 dark:text-amber-300 dark:border-amber-700',
  orange: 'bg-orange-50 text-orange-700 border-orange-400 dark:bg-orange-900/25 dark:text-orange-300 dark:border-orange-600',
  red: 'bg-red-50 text-red-700 border-red-400 dark:bg-red-900/30 dark:text-red-300 dark:border-red-600',
} as const;

/** grade 도트/스파크라인 stroke hex — gray 저채도(gray-400), 상향 강조. */
export const GRADE_DOT_HEX = {
  gray: '#9ca3af', // gray-400
  yellow: '#f59e0b', // amber-500
  orange: '#f97316', // orange-500
  red: '#ef4444', // red-500
} as const;

/** grade 스파크라인 채움 rgba(GRADE_DOT_HEX 동일 톤, gray는 최저 알파). */
export const GRADE_SPARK_FILL = {
  gray: 'rgba(156,163,175,0.08)', // gray-400 @ .08
  yellow: 'rgba(245,158,11,0.12)', // amber-500 @ .12
  orange: 'rgba(249,115,22,0.12)', // orange-500 @ .12
  red: 'rgba(239,68,68,0.14)', // red-500 @ .14
} as const;
