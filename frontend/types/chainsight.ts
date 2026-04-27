/**
 * Chain Sight 타입 정의
 *
 * API 계약 타입: @contracts/shared-types 에서 re-export (single source of truth)
 * FE 전용 타입: 이 파일에서 직접 정의 (ForceGraph, RelationStyle 등)
 */

// ── API 계약 타입 (contracts/shared-types.ts가 single source of truth) ──

export type {
  // Seeds
  SeedReason,
  SeedType,
  SeedNode,
  SectorSummary,
  SeedResponse,
  // Sector Graph
  NodeSize,
  MarketNode,
  MarketEdge,
  SectorGraphResponse,
  // Neighbor Graph
  NeighborRelation,
  Neighbor,
  CrossEdge,
  NeighborResponse,
  // Signal Feed
  ChainCategory,
  ChainStrength,
  ChainPathNode,
  ChainEdge,
  ChainSignal,
  SignalFeedResponse,
  // Deep Dive
  GraphNode,
  GraphEdge,
  GraphMeta,
  GraphResponse,
  // Suggestions
  SuggestionCategory,
  SuggestionsResponse,
  // Trace
  TraceStep,
  TraceResponse,
  // Exploration State
  TrailNode,
} from '@contracts/shared-types';

// ── 관계 타입 시각 체계 (FE 전용) ──

export type RelationType =
  | 'PEER_OF'
  | 'SUPPLIES_TO'
  | 'CUSTOMER_OF'
  | 'COMPETES_WITH'
  | 'CO_MENTIONED'
  | 'HAS_THEME'
  | 'PRICE_CORRELATED'
  | 'BELONGS_TO_SECTOR'
  | 'BELONGS_TO_INDUSTRY'
  | 'RELATED_TO';

export interface RelationStyle {
  color: string;
  label: string;
  dash?: number[];  // 점선 패턴
  width: number;
}

// ── ForceGraph 내부 노드/링크 (FE 전용, react-force-graph 연동) ──

export interface ForceNode {
  id: string;
  ticker: string;
  name: string;
  sector: string;
  market_cap: number;
  pagerank: number;
  isCenter: boolean;
  depth: number;
  [key: string]: unknown;
}

export interface ForceLink {
  source: string;
  target: string;
  relType: RelationType;
  displayType: string;  // derived_type 또는 type
  label: string;
  color: string;
  width: number;
  dash?: number[];
}
