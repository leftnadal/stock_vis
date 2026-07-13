/**
 * Theme Heat 표시 카피 (TH-15/16 v3 렌더) — 프론트 표시 계층 전용.
 * z_mode 근거 문구는 TH-ZMODE-LABEL-FIX 의미 레이어 계약(설계 §2)을 그대로 반영.
 */

/** z_mode → 성분 근거 문구 (의미 레이어). */
export function zModeBasisText(zMode: string | null | undefined): string {
  if (zMode === 'time_series') return '3년 자기 이력 대비 (시계열 기준)';
  if (zMode === 'cross_sectional') return '동일 시점 동종 대비 (횡단면)';
  return '수집 대기';
}

/** 공식 밴드 → Tailwind 색 (온도 표기용). */
export function bandColorClass(band: string | null | undefined): string {
  if (band === 'overheated') return 'text-red-600 dark:text-red-400';
  if (band === 'warning') return 'text-amber-600 dark:text-amber-400';
  if (band === 'cool') return 'text-sky-600 dark:text-sky-400';
  return 'text-gray-400';
}

/** driver.direction → 아이콘·문구 (결정27=B). */
export function directionGlyph(direction: string | null | undefined): { icon: string; verb: string } {
  if (direction === 'up') return { icon: '▲', verb: '견인' };
  if (direction === 'down') return { icon: '▼', verb: '냉각' };
  return { icon: '●', verb: '수준' };
}

/** 성분 status → 뱃지 문구. */
export function componentStatusText(status: string): string {
  if (status === 'computed') return '';
  if (status === 'coldstart') return '수집 대기';
  return '누적 중';
}
