/**
 * 관계 카드 리스트 설정 상수 (⑳-2 S2) — 정렬·표시 항목 단일 소스.
 * (⑳-1 leaderboardConfig 패턴: 매직넘버·매핑을 컴포넌트 밖으로 분리.)
 */

import { getRelationStyle } from './graphStyles';
import type { EgoEdge, EgoNode } from '@/types/chainsight';

/** 기본 표시 개수(더 보기 전) + 더 보기 증가량 */
export const CARD_LIST = {
  initialVisible: 12,
  loadMoreStep: 12,
} as const;

export type CardSortKey = 'confidence' | 'recent';
export const DEFAULT_SORT: CardSortKey = 'confidence';

/**
 * 관계 유형 → 배지(색·라벨). 그래프 RELATION_STYLES 재사용(신규색 0).
 * 기존 범례 용어(공급·경쟁·Peer·동시출현·그룹·관련) 그대로.
 */
export function relationBadge(relationType: string): { color: string; label: string } {
  const s = getRelationStyle(relationType);
  return { color: s.color, label: s.label };
}

/** 이웃 노드 심볼 → 노드 메타 맵(카드가 회사명·섹터 조회용). */
export function buildNodeMap(nodes: EgoNode[]): Record<string, EgoNode> {
  const m: Record<string, EgoNode> = {};
  for (const n of nodes) m[n.symbol] = n;
  return m;
}

/** 카드 정렬: confidence(신뢰도 내림차순, 기본) / recent(최근 언급일 내림차순). */
export function sortEdges(edges: EgoEdge[], sortKey: CardSortKey): EgoEdge[] {
  const copy = [...edges];
  if (sortKey === 'recent') {
    copy.sort((a, b) => (b.last_mentioned ?? '').localeCompare(a.last_mentioned ?? ''));
  } else {
    copy.sort((a, b) => b.truth_score - a.truth_score);
  }
  return copy;
}
