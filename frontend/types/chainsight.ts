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
  // Ego Graph
  EgoTrendPoint,
  EgoTrend,
  EgoNode,
  EgoEdge,
  EgoMeta,
  EgoGraphResponse,
  // Centrality Leaderboard (⑳-1)
  CentralityMetric,
  CentralityLeaderboardItem,
  CentralityTopResponse,
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

// ── Event Board (CS-RD3 이벤트 보드) ──

/** GET /api/v1/chainsight/events/ 응답 항목 */
export interface EventBoardItem {
  theme: string;
  /**
   * ON(event_group)일 때만 존재하는 n3 표시명. OFF(theme_tags)에선 생략 →
   * 라벨은 getLabelForTheme(theme) 폴백(오늘과 IDENTICAL). theme는 ON에선 slug(드릴다운 키).
   */
  name?: string;
  member_count: number;
  /** ⑳-2 S4: 구성 티커 목록(카드 제목 티커 병기). 구버전 응답엔 없을 수 있어 optional. */
  members?: string[];
  avg_return: number;
  avg_score: number;
  high_attention_count: number;
  low_attention_count: number;
}

/** GET /api/v1/chainsight/events/<theme>/stocks/ 응답 항목 */
export interface EventRankingItem {
  symbol: string;
  name: string;
  score: number;
  raw_return: number;
  volume_z: number;
  volatility_pct: number; // 0~1 range
  is_low_liquidity: boolean;

  // M2 leadership metrics (nullable: 게이트 미달 시 백엔드가 NULL 반환)
  trend_quality: number | null; // T2 주신호 — 추세강도
  theme_alpha: number | null; // T3 보조 — 그룹 초과수익
  theme_beta: number | null; // 주신호 — 그룹 민감도
  up_capture: number | null; // 보조 — 상승 포착
  down_capture: number | null; // 보조 — 하락 방어
  capture_spread: number | null; // 주신호 — 주도우위
  is_fallback: boolean; // fallback 산출 여부
}
