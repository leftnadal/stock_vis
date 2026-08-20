/**
 * Mindmap 카드 화면 설정 상수 (CS-P5-FE-CARD B3+B4) — 라벨·검색 매칭 단일 소스.
 * (cardListConfig.ts 패턴 재사용: 매직넘버·매핑을 컴포넌트 밖으로 분리.)
 */

import type {
  MindmapCardSummary,
  MindmapDirection,
  MindmapIndustry,
  MindmapRelationType,
  MindmapSector,
} from '@/types/chainsight';

/** relation_type → 한글 라벨(공급/의존/파트너/경쟁). SEC4종 고정. */
export const MINDMAP_RELATION_LABELS: Record<MindmapRelationType, string> = {
  SUPPLIES_TO: '공급',
  DEPENDS_ON: '의존',
  PARTNER_WITH: '파트너',
  COMPETES_WITH: '경쟁',
};

export function relationTypeLabel(t: string): string {
  return MINDMAP_RELATION_LABELS[t as MindmapRelationType] ?? t;
}

/** direction → 화살표 표기(out=→ 상대 / in=상대 → / both=↔). */
export function directionLabel(direction: MindmapDirection, otherSymbol: string): string {
  if (direction === 'out') return `→ ${otherSymbol}`;
  if (direction === 'in') return `${otherSymbol} →`;
  return `↔ ${otherSymbol}`;
}

/** ACQUIRED role → 표기. */
export function acquiredRoleLabel(role: 'acquirer' | 'target'): string {
  return role === 'acquirer' ? '→ 인수' : '← 피인수';
}

/** 카드 검색 매칭 — 티커/이름 부분일치(대소문자 무시). */
export function cardMatchesQuery(card: MindmapCardSummary, query: string): boolean {
  if (!query.trim()) return true;
  const q = query.trim().toLowerCase();
  return card.ticker.toLowerCase().includes(q) || card.name.toLowerCase().includes(q);
}

export function industryMatchesQuery(industry: MindmapIndustry, query: string): boolean {
  if (!query.trim()) return true;
  return industry.cards.some((c) => cardMatchesQuery(c, query));
}

export function sectorMatchesQuery(sector: MindmapSector, query: string): boolean {
  if (!query.trim()) return true;
  return sector.industries.some((ind) => industryMatchesQuery(ind, query));
}
