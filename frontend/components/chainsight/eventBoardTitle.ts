/**
 * 이벤트 보드 카드 제목 티커 병기 포맷 (⑳-2 S4, 표시 가공).
 * 구성 티커 대문자 병기 우선, 4개 초과 시 "외 N".
 */

export const MEMBER_TITLE_MAX = 4;

/** members → "LRCX · KLAC · TER · AMAT 외 2" (대문자, 상위 MAX + 외 N). */
export function formatMemberTitle(
  members: string[] | undefined,
  max: number = MEMBER_TITLE_MAX,
): string {
  if (!members || members.length === 0) return '';
  const up = members.map((m) => m.toUpperCase());
  if (up.length <= max) return up.join(' · ');
  return `${up.slice(0, max).join(' · ')} 외 ${up.length - max}`;
}
