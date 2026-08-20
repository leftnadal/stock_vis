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
  EgoGrade,
  EgoGradeSource,
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

// ── Theme Heat (TH-15/16, 결정23B/24C/25③/27/29) ──

/** GET /api/v1/chainsight/theme-heat/ 버튼바 항목 (테마당) */
export interface ThemeHeatBarItem {
  theme: string;
  status: 'computed' | 'accumulating';
  score: number | null;        // computed만
  band: 'cool' | 'warning' | 'overheated' | null;
  band_display: string | null; // 냉각/가열/과열
  delta_1d: number | null;
  days: number;
  days_required: number;       // 26
  eta_days: number | null;     // D-n, CV<0.3일 때만
  universe_stale: boolean;
}

/** E2 driver — 결정27 산식 + 결정29 보류 */
export interface ThemeHeatDriver {
  held: boolean;
  reason?: string;
  marker?: string;
  note?: string;
  component?: string;
  label_surface?: string;
  label_technical?: string;
  z?: number;
  contribution_pct?: number;
  basis?: 'delta' | 'level';
  direction?: 'up' | 'down' | 'none';
}

/** E2 성분 (결정25 이중사전 + z_mode) */
export interface ThemeHeatComponent {
  id: string;                  // C1..C8
  label_surface: string;
  label_technical: string;
  z: number | null;
  w: number;
  s: number | null;
  z_mode: 'time_series' | 'cross_sectional' | null;
  status: 'computed' | 'accumulating' | 'coldstart';
}

/** GET /api/v1/chainsight/theme-heat/{theme}/ 카드 */
export interface ThemeHeatCard {
  theme: string;
  as_of: string | null;
  status: 'computed' | 'accumulating';
  score: number | null;
  band: string | null;
  band_display: string | null;
  delta_1d: number | null;
  z_mode: string | null;
  driver: ThemeHeatDriver | null;
  confidence: { present: number; total: number; missing: string[]; renorm_divisor: number } | null;
  components: ThemeHeatComponent[];
  quadrant: { heat: number | null; dss: number | null; dss_status: string; dss_eta: string };
  history: { values: number[]; capacity: number; filled: number };
  days?: number;
  days_required?: number;
  eta_days?: number | null;
  blocked?: { reason: string; since: string | null; days_stale: number | null };
}

// ── Mindmap 카드 (CS-P5-FE-CARD, D1 업종 2단 + D-CARD-GATE) ──

/** 트리 카드 요약 — GET /api/v1/chainsight/mindmap/tree/ 내 industries[].cards[] 항목 */
export interface MindmapCardSummary {
  ticker: string;
  name: string;
  /** 게이트 통과 연결 수(evidence AND SEC4종) */
  gate_conn_count: number;
  /** 같은 그룹(CO_MENTIONED) 신호 수 — 연결 아님 */
  group_signal_count: number;
}

/** 레벨2 — industry 버킷("미분류" 포함 가능) */
export interface MindmapIndustry {
  industry: string;
  stock_count: number;
  cards: MindmapCardSummary[];
}

/** 레벨1 — sector 버킷("미분류" 버킷 포함) */
export interface MindmapSector {
  sector: string;
  stock_count: number;
  industry_count: number;
  industries: MindmapIndustry[];
}

/** GET /api/v1/chainsight/mindmap/tree/ 응답 */
export interface MindmapTreeResponse {
  stock_total: number;
  sector_count: number;
  gate_definition: string;
  sectors: MindmapSector[];
}

/** SEC 4종 게이트 통과 관계 유형 */
export type MindmapRelationType =
  | 'COMPETES_WITH'
  | 'PARTNER_WITH'
  | 'SUPPLIES_TO'
  | 'DEPENDS_ON';

export type MindmapDirection = 'in' | 'out' | 'both';

/** 카드 상세 — "확인된 연결" 항목 */
export interface MindmapConnection {
  other: string;
  other_name: string;
  relation_type: MindmapRelationType;
  direction: MindmapDirection;
  sync_strength: number | null;
  contract_date: string | null;
  truth_score: number;
  status: string;
  basis: string;
}

/** 카드 상세 — ACQUIRED 방향 구조(현재 데이터 0 = 빈 상태 정상) */
export interface MindmapAcquired {
  other: string;
  other_name: string;
  role: 'acquirer' | 'target';
}

/** 카드 상세 — "같은 그룹"(CO_MENTIONED, 연결 아님) */
export interface MindmapGroup {
  other: string;
  other_name: string;
  co_mention_count: number;
}

/** GET /api/v1/chainsight/mindmap/card/{symbol}/ 응답 */
export interface MindmapCardResponse {
  symbol: string;
  name: string;
  connection_count: number;
  connections: MindmapConnection[];
  acquired: MindmapAcquired[];
  groups: MindmapGroup[];
  group_total: number;
  group_capped: boolean;
}
