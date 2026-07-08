/**
 * MP2-TREND — 멀티라인 카테고리 팔레트 단일소스.
 *
 * 기존 색 토큰(sectorColor=방향형 rose/sky, meaning=의미밴드)은 "엔티티 식별"이 아니라
 * "방향/의미" 표현용이라 N개 라인 구분에 부적합. 여기 11색은 **카테고리 식별 전용**.
 * 신규 hex는 이 파일 1곳에만 둔다(산개 금지). 색맹 대비 위해 명도·색상 교차 배열.
 */
export const TREND_PALETTE: readonly string[] = [
  '#2563eb', // blue-600
  '#dc2626', // red-600
  '#16a34a', // green-600
  '#d97706', // amber-600
  '#7c3aed', // violet-600
  '#0891b2', // cyan-600
  '#db2777', // pink-600
  '#65a30d', // lime-600
  '#ea580c', // orange-600
  '#0d9488', // teal-600
  '#9333ea', // purple-600
] as const

/** 강조되지 않은 라인 색(감쇠) — 회색 단일. */
export const TREND_MUTED = '#cbd5e1' // slate-300

/** 인덱스 → 팔레트 색(순환). 적용처가 color 미지정 시 사용. */
export function trendColor(index: number): string {
  return TREND_PALETTE[index % TREND_PALETTE.length]
}
