/**
 * Ego API 어댑터 — 순수 변환 함수 (React 의존성 없음)
 *
 * MarketGraphCanvas Neighbor 모드에서 ego API 응답을
 * buildNeighborGraph가 소비하는 형태로 변환한다.
 *
 * 분리 이유: vitest에서 React 없이 단독 테스트 가능하게 하기 위해
 */

import type {
  EgoGraphResponse,
  EgoNode,
  Neighbor,
  CrossEdge,
  GraphResponse,
  GraphNode,
  GraphEdge,
} from '@/types/chainsight';

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

/**
 * EgoGraphResponse → GraphResponse(레거시 Neo4j graph 계약)로 매핑.
 *
 * ⑳-3 S1: /chainsight/[symbol] 표면과 GraphMiniView가 소비하던 레거시 Neo4j
 * `/graph/` 응답 형태(GraphResponse)를 PG ego 응답에서 재구성한다. GraphCanvas·
 * GraphMiniView 렌더 로직 무변경으로 데이터 소스만 PG ego로 전환하기 위한 순수 어댑터.
 *
 * 매핑 규칙:
 *  - center: ego.center(symbol→ticker), sector는 ego.nodes에서 조회(center 객체엔 없음)
 *  - nodes: ego.nodes에서 center 제외(symbol→ticker, sector 유지)
 *  - edges: ego.edges(source→from, target→to, relation_type→type). derived_type 없음
 *    (GraphCanvas는 `derived_type || type`로 폴백하므로 type만으로 렌더 정상)
 *  - meta: node_count=center+이웃, edge_count=edges, query_ms=0(PG는 미측정)
 *
 * ego 미제공 필드(market_cap·pagerank_score·growth_stage·capital_dna)는 생략 →
 * GraphNode의 optional이라 렌더 시 기본값/조건부 미표시로 안전 수렴.
 */
export function egoToGraphResponse(ego: EgoGraphResponse): GraphResponse {
  const nodeInfo = new Map<string, EgoNode>(ego.nodes.map((n) => [n.symbol, n]));
  const centerSym = ego.center.symbol;

  const center: GraphNode = {
    ticker: centerSym,
    name: ego.center.name || centerSym,
    sector: nodeInfo.get(centerSym)?.sector ?? '',
  };

  const nodes: GraphNode[] = ego.nodes
    .filter((n) => n.symbol !== centerSym)
    .map((n) => ({
      ticker: n.symbol,
      name: n.name || n.symbol,
      sector: n.sector ?? '',
    }));

  const edges: GraphEdge[] = ego.edges.map((e) => ({
    from: e.source,
    to: e.target,
    type: e.relation_type,
  }));

  return {
    center,
    nodes,
    edges,
    meta: {
      depth: 1,
      node_count: nodes.length + 1,
      edge_count: edges.length,
      query_ms: 0,
    },
  };
}
