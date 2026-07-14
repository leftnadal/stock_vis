/**
 * Ego API 어댑터 — 순수 변환 함수 (React 의존성 없음)
 *
 * MarketGraphCanvas Neighbor 모드에서 ego API 응답을
 * buildNeighborGraph가 소비하는 형태로 변환한다.
 *
 * 분리 이유: vitest에서 React 없이 단독 테스트 가능하게 하기 위해
 */

import type { EgoGraphResponse, EgoNode, Neighbor, CrossEdge } from '@/types/chainsight';

// ── 시각 인코딩 상수 ──

/**
 * 시각 인코딩 채널 2개:
 *  ⑴ truth_score → 선 굵기 (egoTruthScoreToWidth)
 *  ⑵ trend.direction → 색 힌트 (egoTrendToColor, flat이면 기본색 유지)
 */
export const EGO_TREND_COLOR_UP   = '#22C55E';  // green-500 — trend up
export const EGO_TREND_COLOR_DOWN = '#EF4444';  // red-500  — trend down

/**
 * ego truth_score(0~100)를 링크 굵기로 변환.
 * 기존 EDGE_WIDTHS 계층과 충돌하지 않도록 ego 전용 보정(1~4px).
 */
export function egoTruthScoreToWidth(score: number): number {
  // 0~100 → 1~4px 선형 보간
  return 1 + (Math.min(100, Math.max(0, score)) / 100) * 3;
}

/**
 * ego trend.direction을 링크 색으로 변환.
 * flat이면 null 반환 → 호출측에서 EDGE_COLORS 기본색 사용.
 */
export function egoTrendToColor(direction: 'up' | 'down' | 'flat'): string | null {
  if (direction === 'up')   return EGO_TREND_COLOR_UP;
  if (direction === 'down') return EGO_TREND_COLOR_DOWN;
  return null; // flat → 기본 색 유지
}

/**
 * EgoGraphResponse → buildNeighborGraph이 소비하는 형태로 매핑.
 *
 * 매핑 규칙:
 *  - center: ego.center (symbol, name, 나머지 필드는 기본값)
 *  - neighbors: ego.edges 각 항목에서 target=이웃 심볼, relation.type=relation_type
 *  - cross_edges: [] — ego는 2-hop 미제공
 *  - seed_reasons: [] — ego는 seed 정보 미제공
 *
 * EgoNode 조회: ego.nodes 배열에서 symbol로 sector 찾기.
 */
export function egoToNeighborShape(ego: EgoGraphResponse): {
  center: any;
  neighbors: Neighbor[];
  cross_edges: CrossEdge[];
} {
  const nodeMap = new Map<string, EgoNode>(ego.nodes.map((n) => [n.symbol, n]));

  const neighbors: Neighbor[] = ego.edges.map((edge) => {
    const neighborSymbol = edge.source === ego.center.symbol ? edge.target : edge.source;
    const nodeInfo = nodeMap.get(neighborSymbol);

    return {
      symbol: neighborSymbol,
      name: nodeInfo?.name ?? neighborSymbol,
      sector: nodeInfo?.sector ?? '',
      industry: '',
      market_cap: 0,
      daily_return: 0,
      volume_ratio: 0,
      is_seed: false,
      seed_type: null,
      seed_reasons: [],  // ego는 seed 정보 미제공
      relation: {
        type: edge.relation_type,
        display_type: edge.relation_type,
        direction: (edge.source === ego.center.symbol ? 'outbound' : 'inbound') as 'outbound' | 'inbound',
        truth_score: edge.truth_score,
        market_score: null,
        status: 'active',
        relation_category: 'truth',
        evidence_tier: null,
        // ego 전용 시각 인코딩 데이터
        _ego_trend_direction: edge.trend.direction as 'up' | 'down' | 'flat',
      },
    } as Neighbor & { relation: Neighbor['relation'] & { _ego_trend_direction?: 'up' | 'down' | 'flat' } };
  });

  return {
    center: {
      symbol: ego.center.symbol,
      name: ego.center.name,
      sector: '',
      industry: '',
      market_cap: 0,
      daily_return: 0,
      volume_ratio: 0,
      is_seed: false,
      seed_type: null,
      seed_reasons: [],  // ego는 seed 정보 미제공
    },
    neighbors,
    cross_edges: [],  // ego는 2-hop 미제공
  };
}
