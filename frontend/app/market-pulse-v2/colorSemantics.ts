/**
 * market-pulse-v2 구획 방향성 색 시맨틱 단일소스 — 한국축(DECISIONS D-COLOR-SYSTEM).
 *
 *   상승 · 강세 · 유입 · 긍정 = rose(빨강)
 *   하락 · 약세 · 유출 · 부정 = sky(파랑)
 *   중립 = slate
 *
 * 값은 `sectorColor.ts`(rose #f43f5e / sky #0ea5e9)와 정합(구획 내 direction drift 방지).
 * dashboard `components/eod/colorSemantics.ts`와 값 정합(import 금지 — 구획별 로컬 소스, COLOR-TOKEN-PROMOTE 대기).
 *
 * ⚠ 위기(CRISIS)·약세는 색이 sky로 이동 — 경고성은 색이 아닌 **라벨**(위기/약세 텍스트)이 보존한다
 *    (D-COLOR-SYSTEM: 색 단독 인코딩 금지, 라벨 병기 불변). 경고성 정보 손실 금지.
 * ⚠ 비방향 색은 이 축 대상 아님(무변경): 집중도 쏠림 강도(FLOW_TONE)·이상신호 경고·데이터 신선도·
 *    뉴스 카테고리 팔레트. 방향(등락·강약·유입유출·긍정부정)만 이 토큰을 소비한다.
 * ⚠ Tailwind 정적 리터럴만(퍼지 안전) — 동적 클래스명 생성 금지.
 */

/** 방향 의미 밴드(bg+text+border) — regime/breadth/flow 의미밴드 소비. */
export const DIRECTION_BAND = {
  positive: 'bg-rose-50 text-rose-800 border-rose-200',
  negative: 'bg-sky-50 text-sky-800 border-sky-200',
  neutral: 'bg-slate-50 text-slate-700 border-slate-200',
} as const

/** 방향 텍스트 색 — 상승/강세 rose / 하락/약세 sky. */
export const DIRECTION_TEXT = {
  positive: 'text-rose-600',
  negative: 'text-sky-600',
} as const

/** 보조 통계(신고가/신저가 등) 약한 강조 텍스트 색. */
export const DIRECTION_TEXT_SOFT = {
  positive: 'text-rose-500',
  negative: 'text-sky-500',
} as const
