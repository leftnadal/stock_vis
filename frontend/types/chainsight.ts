/**
 * Chain Sight 타입 정의
 */

// ── Graph API 응답 ──

export interface GraphNode {
  ticker: string;
  name?: string;
  sector?: string;
  industry?: string;
  market_cap?: number;
  growth_stage?: string;
  capital_dna?: string;
  pagerank_score?: number;
  community_id?: number;
  [key: string]: unknown;
}

export interface GraphEdge {
  from: string;
  to: string;
  type: string;            // PEER_OF, SUPPLIES_TO, BELONGS_TO_INDUSTRY, etc.
  derived_type?: string;   // CUSTOMER_OF (역방향)
  props?: Record<string, unknown>;
  market_signals?: {
    co_mention_count?: number;
    price_correlation?: number;
  };
}

export interface GraphMeta {
  depth: number;
  node_count: number;
  edge_count: number;
  query_ms: number;
}

export interface GraphResponse {
  center: GraphNode;
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta: GraphMeta;
}

// ── Suggestions API 응답 ──

export interface SuggestionCategory {
  id: string;           // peers, same_industry, co_mentioned, same_sector
  label: string;        // 경쟁사, 같은 산업, 뉴스 동시출현, 같은 섹터
  count: number;
  rel_types: string[];
  top_tickers: string[];
  strength: 'strong' | 'moderate' | 'signal' | 'weak';
}

export interface SuggestionsResponse {
  symbol: string;
  categories: SuggestionCategory[];
}

// ── Trace API 응답 ──

export interface TraceStep {
  node: GraphNode;
  next_relation: {
    from: string;
    to: string;
    type: string;
    props?: Record<string, unknown>;
  } | null;
}

export interface TraceResponse {
  from: string;
  to: string;
  found: boolean;
  path_length: number;
  path: TraceStep[];
  error?: string;
}

// ── 관계 타입 시각 체계 ──

export type RelationType =
  | 'PEER_OF'
  | 'SUPPLIES_TO'
  | 'CUSTOMER_OF'
  | 'COMPETES_WITH'
  | 'CO_MENTIONED'
  | 'HAS_THEME'
  | 'BELONGS_TO_SECTOR'
  | 'BELONGS_TO_INDUSTRY'
  | 'RELATED_TO';

export interface RelationStyle {
  color: string;
  label: string;
  dash?: number[];  // 점선 패턴
  width: number;
}

// ── ForceGraph 내부 노드/링크 ──

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
