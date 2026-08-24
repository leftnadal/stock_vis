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

// ── R1 Phase C-1: 카드 필터·정렬 (트리 화면) ──

/** 연결 유무 필터. all=전체, has_conn=gate_conn_count>0, no_conn=gate_conn_count===0. */
export type MindmapFilterMode = 'all' | 'has_conn' | 'no_conn';

/** 정렬 키. none=기존 순서(ticker), conn_*=gate_conn_count, group_*=group_signal_count. */
export type MindmapSortKey = 'none' | 'conn_desc' | 'conn_asc' | 'group_desc' | 'group_asc';

export const MINDMAP_FILTER_OPTIONS: { value: MindmapFilterMode; label: string }[] = [
  { value: 'all', label: '전체' },
  { value: 'has_conn', label: '연결 있음' },
  { value: 'no_conn', label: '연결 없음' },
];

export const MINDMAP_SORT_OPTIONS: { value: MindmapSortKey; label: string }[] = [
  { value: 'none', label: '기본순' },
  { value: 'conn_desc', label: '연결 많은순' },
  { value: 'conn_asc', label: '연결 적은순' },
  { value: 'group_desc', label: '그룹 많은순' },
  { value: 'group_asc', label: '그룹 적은순' },
];

/** 카드 필터 매칭 — 연결 유무 토글. */
export function cardMatchesFilter(card: MindmapCardSummary, filterMode: MindmapFilterMode): boolean {
  if (filterMode === 'has_conn') return card.gate_conn_count > 0;
  if (filterMode === 'no_conn') return card.gate_conn_count === 0;
  return true;
}

/** 검색+필터 동시 매칭 — 트리 화면 카드 가시성 단일 판정. */
export function cardVisible(
  card: MindmapCardSummary,
  query: string,
  filterMode: MindmapFilterMode,
): boolean {
  return cardMatchesQuery(card, query) && cardMatchesFilter(card, filterMode);
}

export function industryHasVisibleCard(
  industry: MindmapIndustry,
  query: string,
  filterMode: MindmapFilterMode,
): boolean {
  return industry.cards.some((c) => cardVisible(c, query, filterMode));
}

export function sectorHasVisibleCard(
  sector: MindmapSector,
  query: string,
  filterMode: MindmapFilterMode,
): boolean {
  return sector.industries.some((ind) => industryHasVisibleCard(ind, query, filterMode));
}

/** 카드 정렬 — 'none'은 입력 순서(기존 ticker 순) 그대로 반환, 그 외는 안정 정렬 신규 배열. */
export function sortCards(cards: MindmapCardSummary[], sortKey: MindmapSortKey): MindmapCardSummary[] {
  if (sortKey === 'none') return cards;
  const sorted = [...cards];
  switch (sortKey) {
    case 'conn_desc':
      sorted.sort((a, b) => b.gate_conn_count - a.gate_conn_count);
      break;
    case 'conn_asc':
      sorted.sort((a, b) => a.gate_conn_count - b.gate_conn_count);
      break;
    case 'group_desc':
      sorted.sort((a, b) => b.group_signal_count - a.group_signal_count);
      break;
    case 'group_asc':
      sorted.sort((a, b) => a.group_signal_count - b.group_signal_count);
      break;
  }
  return sorted;
}
