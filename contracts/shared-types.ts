/**
 * contracts/shared-types.ts
 * 프론트엔드 공유 타입 — contracts/*.yaml + frontend/types/ 기반 생성
 *
 * @frontend 에이전트는 이 파일의 타입을 기준으로 API 호출 코드를 작성한다.
 * @backend 에이전트가 API 스펙을 변경하면 이 파일도 함께 업데이트한다.
 *
 * 실제 구현: frontend/types/chainsight.ts 기준 (2026-04-12 검증)
 */

// ──────────────── Chain Sight: Seeds ────────────────

export type SeedReason =
  | 'price_top5'
  | 'price_bottom5'
  | 'volume_surge'
  | 'sector_outlier'
  | 'relation_upgrade'
  | 'relation_downgrade'
  | 'relation_new'
  | 'comention_surge';

export type SeedType = 'price' | 'volume' | 'relation' | 'comention';

export interface SeedNode {
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  daily_return: number;
  volume_ratio: number;
  seed_reasons: SeedReason[];
  seed_type: SeedType;
  signal_count: number;
}

export interface SectorSummary {
  sector: string;
  sector_display: string;
  pct_change: number;
  seed_count: number;
  heat_total: number;
  top_seed: string | null;
}

export interface SeedResponse {
  date: string;
  total_seeds: number;
  sector_summary: SectorSummary[];
  seeds: SeedNode[];
}

// ──────────────── Chain Sight: Sector Graph ────────────────

export type NodeSize = 'xl' | 'lg' | 'md' | 'sm';

export interface MarketNode {
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  daily_return: number;
  volume_ratio: number;
  is_seed: boolean;
  seed_type: string | null;
  seed_reasons: string[];
  node_size: NodeSize;
}

export interface MarketEdge {
  source: string;
  target: string;
  type: string;
  relation_category: string;
  truth_score: number | null;
  market_score: number | null;
  status: string;
}

export interface SectorGraphResponse {
  sector: string;
  node_count: number;
  edge_count: number;
  nodes: MarketNode[];
  edges: MarketEdge[];
}

// ──────────────── Chain Sight: Neighbor Graph ────────────────

export interface NeighborRelation {
  type: string;
  display_type: string;        // CUSTOMER_OF는 SUPPLIES_TO 역방향 파생
  direction: 'inbound' | 'outbound';
  truth_score: number | null;
  market_score: number | null;
  status: string;
  relation_category: string;
  evidence_tier: number | null;
}

export interface Neighbor {
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  daily_return: number;
  volume_ratio: number;
  is_seed: boolean;
  seed_type: string | null;
  seed_reasons: string[];
  relation: NeighborRelation;
}

export interface CrossEdge {
  source: string;
  target: string;
  type: string;
  truth_score: number | null;
}

export interface NeighborResponse {
  center: MarketNode & { is_seed: boolean; seed_type: string | null; seed_reasons: string[] };
  neighbors: Neighbor[];
  cross_edges: CrossEdge[];
  total_neighbor_count: number;
  returned_count: number;
  truncated: boolean;
}

// ──────────────── Chain Sight: Signal Feed ────────────────

export type ChainCategory =
  | 'supply_chain'
  | 'competition'
  | 'co_mention'
  | 'price_correlation'
  | 'peer_network';

export type ChainStrength = 'strong' | 'moderate' | 'weak';

export interface ChainPathNode {
  symbol: string;
  name: string;
  sector: string;
}

export interface ChainEdge {
  type: string;
  score: number;
}

export interface ChainSignal {
  id: string;                     // chain_{date}_{seq:03d}
  title: string;                  // {from} → {to} chain
  category: ChainCategory;
  strength: ChainStrength;
  total_confidence: number;       // mean*0.7 + min*0.3
  trigger_summary: string;
  root_sector: string;
  path: ChainPathNode[];
  edges: ChainEdge[];
}

export interface SignalFeedResponse {
  date: string;
  page: number;
  page_size: number;
  total_count: number;
  has_next: boolean;
  chains: ChainSignal[];
}

// ──────────────── Chain Sight: Deep Dive ────────────────

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
  type: string;
  derived_type?: string;          // CUSTOMER_OF (역방향)
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

// ──────────────── Chain Sight: Suggestions ────────────────

export interface SuggestionCategory {
  id: 'peers' | 'same_industry' | 'co_mentioned' | 'same_sector';
  label: string;
  count: number;
  rel_types: string[];
  top_tickers: string[];
  strength: 'strong' | 'moderate' | 'signal' | 'weak';
}

export interface SuggestionsResponse {
  symbol: string;
  categories: SuggestionCategory[];
}

// ──────────────── Chain Sight: Trace ────────────────

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

// ──────────────── Chain Sight: 탐색 상태 ────────────────

export interface TrailNode {
  symbol: string;
  type: 'sector' | 'stock';
  depth: number;
  relation_from_prev?: string;
  seed_type?: SeedType | null;
}

// ──────────────── Validation ────────────────

export type ValidationSignal = 'green' | 'yellow' | 'red' | 'gray';

export interface CategorySignal {
  category: string;
  display_name: string;
  signal: ValidationSignal;
  description: string;
  metric_count: number;
  signal_reason: string;
}

export interface IndustryLeader {
  symbol: string;
  name: string;
  market_cap: number | null;
}

export interface PeerInfo {
  peer_count: number;
  confidence: string;
  benchmark_basis: string;
  size_bucket: string;
  basis_description: string;
  top_peers: string[];
  industry_leader: IndustryLeader | null;
}

export interface IndustryRank {
  metric: string;
  display_name: string;
  rank: number;
  total: number;
  value: number | null;
}

export interface ValidationSummaryResponse {
  symbol: string;
  company_name: string;
  data_fiscal_year: number;
  data_freshness: string | null;
  category_signals: CategorySignal[];
  summary_text: string;
  summary_source: 'rule';
  peer_info: PeerInfo | null;
  industry_position: { ranks: IndustryRank[] };
}

// ──────────────── SEC Pipeline ────────────────

export type SupplyChainRelationType = 'PARTNER_WITH' | 'CUSTOMER_OF' | 'DEPENDS_ON';
export type ConfidenceGrade = 'A' | 'B' | 'C';

export interface SupplyChainEntry {
  company_name: string;
  matched_ticker: string | null;
  relation_type: SupplyChainRelationType;
  confidence_grade: ConfidenceGrade;
}

export interface FilingEntry {
  filing_type: string;
  filed_date: string;
  supply_chain: SupplyChainEntry[];
  business_model: Record<string, unknown> | null;
}

export interface FilingDataResponse {
  symbol: string;
  filings: FilingEntry[];
}

// ──────────────── Thesis Control ────────────────

export type ThesisState =
  | 'active'
  | 'monitoring'
  | 'paused'
  | 'expired'
  | 'archived';

export interface ArrowDisplay {
  degree: number; // 0~180
  color: string;  // hex (#2563EB, #60A5FA, #D1D5DB, #FB923C, #EF4444)
  label: string;  // "강하게 지지" ~ "강하게 반박"
}

export interface MoonPhase {
  overall_score: number; // -1 ~ 1
  brightness: number;    // 0 ~ 1
}
