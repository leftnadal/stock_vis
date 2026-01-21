# Stock-Vis Screen Data Structure v1.0.0

## 화면별 데이터 구조 명세

**버전**: 1.0.0  
**최종 수정**: 2025-12-13  
**관련 문서**: AI_ANALYSIS_v1.0.0_OVERVIEW.md

---

## 📋 목차

1. [개요](#1-개요)
2. [DataBasket 관련 구조](#2-databasket-관련-구조)
3. [Analysis Session 구조](#3-analysis-session-구조)
4. [Graph Visualization 구조](#4-graph-visualization-구조)
5. [API Response 구조](#5-api-response-구조)
6. [SSE Event 구조](#6-sse-event-구조)
7. [Cache 데이터 구조](#7-cache-데이터-구조)

---

## 1. 개요

### 1.1 문서 목적

이 문서는 Stock-Vis AI Analysis 시스템의 화면별 데이터 구조를 정의합니다.
프론트엔드와 백엔드 간 데이터 교환 형식을 명확히 하여 개발 효율성을 높입니다.

### 1.2 공통 규칙

```typescript
// 공통 응답 래퍼
interface APIResponse<T> {
  success: boolean;
  data: T;
  error?: {
    code: string;
    message: string;
  };
  meta?: {
    timestamp: string;
    request_id: string;
  };
}

// 페이지네이션
interface PaginatedResponse<T> extends APIResponse<T[]> {
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}
```

---

## 2. DataBasket 관련 구조

### 2.1 DataBasket (바구니)

```typescript
interface DataBasket {
  id: number;
  name: string;
  description: string;
  items: BasketItem[];
  items_count: number;
  can_add_item: boolean;  // items_count < 15
  created_at: string;     // ISO 8601
  updated_at: string;
}

// 예시
{
  "id": 1,
  "name": "반도체 분석 바구니",
  "description": "반도체 섹터 종목 및 관련 뉴스",
  "items": [...],
  "items_count": 5,
  "can_add_item": true,
  "created_at": "2025-12-13T10:00:00Z",
  "updated_at": "2025-12-13T14:30:00Z"
}
```

### 2.2 BasketItem (바구니 아이템)

```typescript
type ItemType = 'stock' | 'news' | 'financial' | 'macro';

interface BasketItem {
  id: number;
  item_type: ItemType;
  item_type_display: string;  // 한글 표시명
  reference_id: string;       // 종목코드, 뉴스ID 등
  title: string;
  subtitle: string;
  data_snapshot: StockSnapshot | NewsSnapshot | FinancialSnapshot | MacroSnapshot;
  snapshot_date: string;      // YYYY-MM-DD
  created_at: string;
}
```

### 2.3 Data Snapshots (스냅샷 타입별)

```typescript
// 종목 스냅샷
interface StockSnapshot {
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  pe_ratio: number | null;
  pb_ratio: number | null;
  dividend_yield: number | null;
  high_52w: number;
  low_52w: number;
  current_price: number;
  price_change_percent: number;
}

// 뉴스 스냅샷
interface NewsSnapshot {
  news_id: string;
  title: string;
  summary: string;
  source: string;
  published_date: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  sentiment_score: number;  // -1.0 ~ 1.0
  related_stocks: string[];
  url: string;
}

// 재무제표 스냅샷
interface FinancialSnapshot {
  period: string;           // "2024-Q3", "2024-FY"
  period_type: 'quarterly' | 'annual';
  revenue: number;
  operating_income: number;
  net_income: number;
  eps: number;
  revenue_growth_yoy: number;
  operating_margin: number;
  net_margin: number;
}

// 거시경제 스냅샷
interface MacroSnapshot {
  indicator_code: string;   // "GDP", "CPI", "UNEMPLOYMENT"
  indicator_name: string;
  value: number;
  unit: string;
  date: string;
  previous_value: number;
  change: number;
  change_percent: number;
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
}
```

### 2.4 바구니 아이템 추가 요청

```typescript
// POST /api/v1/rag/baskets/{id}/add_item/
interface AddItemRequest {
  item_type: ItemType;
  reference_id: string;
  title: string;
  subtitle?: string;
  data_snapshot: object;
}

// 응답
interface AddItemResponse {
  success: boolean;
  data: BasketItem;
  error?: {
    code: 'BASKET_FULL' | 'DUPLICATE_ITEM' | 'INVALID_TYPE';
    message: string;
  };
}
```

---

## 3. Analysis Session 구조

### 3.1 AnalysisSession (분석 세션)

```typescript
type SessionStatus = 'active' | 'completed' | 'error';

interface AnalysisSession {
  id: number;
  basket: DataBasket | null;
  status: SessionStatus;
  title: string;
  exploration_path: ExplorationStep[];
  messages: AnalysisMessage[];
  created_at: string;
  updated_at: string;
}

interface ExplorationStep {
  type: 'stock' | 'sector' | 'concept';
  id: string;
  reason: string;
  timestamp: string;
}
```

### 3.2 AnalysisMessage (분석 메시지)

```typescript
type MessageRole = 'user' | 'assistant' | 'system';

interface AnalysisMessage {
  id: number;
  role: MessageRole;
  content: string;
  suggestions: Suggestion[];
  input_tokens: number;
  output_tokens: number;
  created_at: string;
}

interface Suggestion {
  symbol: string;
  reason: string;
  type?: 'competitor' | 'supplier' | 'sector_peer' | 'related';
}

// 예시
{
  "id": 42,
  "role": "assistant",
  "content": "TSMC의 2024년 4분기 실적은...",
  "suggestions": [
    {
      "symbol": "005930.KS",
      "reason": "파운드리 경쟁사로 비교 분석 가능",
      "type": "competitor"
    },
    {
      "symbol": "NVDA",
      "reason": "주요 고객사로 수요 동향 파악에 유용",
      "type": "related"
    }
  ],
  "input_tokens": 580,
  "output_tokens": 1250,
  "created_at": "2025-12-13T14:32:15Z"
}
```

### 3.3 분석 요청

```typescript
// POST /api/v1/rag/sessions/{id}/chat/stream/
interface AnalysisRequest {
  message: string;
  options?: {
    include_graph: boolean;
    max_suggestions: number;
    complexity_override?: 'simple' | 'moderate' | 'complex';
  };
}
```

---

## 4. Graph Visualization 구조

### 4.1 Graph Data (전체 그래프)

```typescript
interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta: GraphMeta;
}

interface GraphMeta {
  total_nodes: number;
  total_edges: number;
  depth: number;
  center_node: string;
  generated_at: string;
}
```

### 4.2 GraphNode (노드)

```typescript
type NodeType = 'stock' | 'sector' | 'news' | 'concept';

interface GraphNode {
  id: string;
  label: string;
  type: NodeType;
  data: StockNodeData | SectorNodeData | NewsNodeData | ConceptNodeData;
  position?: { x: number; y: number };
  style?: NodeStyle;
}

interface StockNodeData {
  symbol: string;
  name: string;
  sector: string;
  market_cap: number;
  price_change: number;
  sentiment_score?: number;
}

interface SectorNodeData {
  name: string;
  stock_count: number;
  avg_change: number;
}

interface NewsNodeData {
  title: string;
  source: string;
  sentiment: string;
  date: string;
}

interface ConceptNodeData {
  name: string;
  description: string;
  relevance: number;
}

interface NodeStyle {
  size: number;
  color: string;
  borderWidth: number;
  borderColor: string;
  opacity: number;
}
```

### 4.3 GraphEdge (엣지)

```typescript
type EdgeType = 
  | 'SUPPLIES'        // 공급
  | 'SUPPLIED_BY'     // 공급받음
  | 'COMPETES_WITH'   // 경쟁
  | 'BELONGS_TO'      // 소속 (섹터)
  | 'MENTIONED_IN'    // 뉴스 언급
  | 'RELATED_TO';     // 일반 관계

interface GraphEdge {
  id: string;
  source: string;     // source node id
  target: string;     // target node id
  type: EdgeType;
  label?: string;
  data: EdgeData;
  style?: EdgeStyle;
}

interface EdgeData {
  strength: number;   // 0.0 ~ 1.0
  bidirectional: boolean;
  metadata?: Record<string, any>;
}

interface EdgeStyle {
  width: number;
  color: string;
  dashed: boolean;
  opacity: number;
}
```

### 4.4 Progressive Graph Loading

```typescript
// GET /api/v1/rag/graph/{symbol}?depth=1
interface GraphRequest {
  symbol: string;
  depth: 1 | 2 | 3;
  include_news: boolean;
  limit_per_type?: number;
}

// 점진적 로딩 응답
interface ProgressiveGraphResponse {
  phase: 'initial' | 'expanded' | 'complete';
  data: GraphData;
  has_more: boolean;
  next_depth?: number;
}
```

### 4.5 Minimal Graph Format (압축)

```typescript
// 대역폭 최적화용 압축 포맷
interface MinimalGraphData {
  n: MinimalNode[];  // nodes
  e: MinimalEdge[];  // edges
}

interface MinimalNode {
  i: string;         // id
  l: string;         // label
  t: string;         // type (s=stock, c=sector, n=news)
  d: object;         // data (축약)
}

interface MinimalEdge {
  s: string;         // source
  t: string;         // target
  y: string;         // type
  w: number;         // weight/strength
}
```

---

## 5. API Response 구조

### 5.1 바구니 목록

```typescript
// GET /api/v1/rag/baskets/
interface BasketsListResponse {
  success: true;
  data: DataBasket[];
  pagination: {
    page: 1,
    page_size: 20,
    total_count: 3,
    total_pages: 1
  };
}
```

### 5.2 세션 생성

```typescript
// POST /api/v1/rag/sessions/
interface CreateSessionRequest {
  basket_id: number;
  title?: string;
}

interface CreateSessionResponse {
  success: true;
  data: AnalysisSession;
}
```

### 5.3 종목 관계 조회

```typescript
// GET /api/v1/rag/stocks/{symbol}/relationships/
interface StockRelationshipsResponse {
  success: true;
  data: {
    symbol: string;
    supply_chain: RelatedStock[];
    competitors: RelatedStock[];
    sector_peers: RelatedStock[];
    _meta: {
      depth: number;
      source: 'neo4j' | 'fallback';
      cached: boolean;
      _error?: string;
    };
  };
}

interface RelatedStock {
  symbol: string;
  name: string;
  relationship?: string;
  strength?: number;
  overlap?: number;
}
```

### 5.4 에러 응답

```typescript
interface ErrorResponse {
  success: false;
  error: {
    code: ErrorCode;
    message: string;
    details?: Record<string, any>;
  };
  meta: {
    timestamp: string;
    request_id: string;
  };
}

type ErrorCode =
  | 'VALIDATION_ERROR'
  | 'NOT_FOUND'
  | 'BASKET_FULL'
  | 'DUPLICATE_ITEM'
  | 'SESSION_EXPIRED'
  | 'RATE_LIMITED'
  | 'LLM_ERROR'
  | 'GRAPH_ERROR'
  | 'INTERNAL_ERROR';
```

---

## 6. SSE Event 구조

### 6.1 분석 스트리밍 이벤트

```typescript
// SSE: /api/v1/rag/sessions/{id}/chat/stream/

type SSEEventPhase =
  | 'cache_check'
  | 'cache_hit'
  | 'cache_miss'
  | 'classifying'
  | 'classified'
  | 'extracting'
  | 'entities_extracted'
  | 'searching'
  | 'search_complete'
  | 'ranking'
  | 'ranking_complete'
  | 'compressing'
  | 'compression_complete'
  | 'analyzing'
  | 'streaming'
  | 'complete'
  | 'error';

interface SSEEvent {
  phase: SSEEventPhase;
  message?: string;
  chunk?: string;
  data?: SSEEventData;
}
```

### 6.2 단계별 이벤트 데이터

```typescript
// cache_hit
interface CacheHitData {
  similarity: number;
  original_question: string;
  latency_ms: number;
}

// classified
interface ClassifiedData {
  complexity: 'simple' | 'moderate' | 'complex';
  token_budget: number;
}

// entities_extracted
interface EntitiesExtractedData {
  stocks: string[];
  metrics: string[];
  concepts: string[];
  timeframe: string | null;
}

// search_complete
interface SearchCompleteData {
  candidates: number;
}

// ranking_complete
interface RankingCompleteData {
  selected: number;
  top_scores: number[];
}

// compression_complete
interface CompressionCompleteData {
  original_tokens: number;
  compressed_tokens: number;
  reduction: string;  // "68%"
}

// complete
interface CompleteData {
  content: string;
  suggestions: Suggestion[];
  usage: {
    input_tokens: number;
    output_tokens: number;
    model: string;
  };
  optimization?: {
    original_context_tokens: number;
    optimized_context_tokens: number;
    token_reduction: string;
  };
  latency_ms: number;
  from_cache: boolean;
  complexity?: string;
}

// error
interface ErrorData {
  message: string;
  code?: string;
  recoverable: boolean;
}
```

### 6.3 SSE 클라이언트 처리 예시

```typescript
// Frontend SSE 처리
const eventSource = new EventSource(`/api/v1/rag/sessions/${sessionId}/chat/stream/`, {
  method: 'POST',
  body: JSON.stringify({ message: question }),
});

eventSource.onmessage = (event) => {
  const data: SSEEvent = JSON.parse(event.data);
  
  switch (data.phase) {
    case 'streaming':
      appendToResponse(data.chunk);
      break;
    case 'complete':
      finalizeResponse(data.data);
      break;
    case 'error':
      handleError(data.data);
      break;
    default:
      updateProgress(data.phase, data.message);
  }
};
```

---

## 7. Cache 데이터 구조

### 7.1 Redis Cache Keys

```typescript
// 캐시 키 패턴
const CACHE_KEYS = {
  // 그래프 컨텍스트
  GRAPH_CONTEXT: 'graph:{symbol}',           // TTL: 1h
  
  // LLM 응답
  LLM_RESPONSE: 'llm:{question_hash}:{entities_hash}',  // TTL: 6h
  
  // 종목 요약
  STOCK_SUMMARY: 'stock_summary:{symbol}',   // TTL: 6h
  
  // 뉴스 요약
  NEWS_SUMMARY: 'news_summary:{news_id}',    // TTL: 24h
  
  // 세션 컨텍스트
  SESSION_CONTEXT: 'session:{session_id}',   // TTL: 30m
};
```

### 7.2 Semantic Cache (Neo4j)

```typescript
// Neo4j AnalysisCache 노드
interface AnalysisCacheNode {
  id: string;                    // UUID
  question: string;
  question_embedding: number[];  // 384-dim vector
  response: string;
  suggestions: string;           // JSON string
  input_tokens: number;
  output_tokens: number;
  user_id: number | null;
  session_id: number | null;
  created_at: string;            // datetime
  expires_at: string;            // datetime (TTL 7d)
}

// 관계: (AnalysisCache)-[:ANALYZED]->(Stock)
```

### 7.3 Cache Hit Response

```typescript
interface CacheHitResponse {
  cache_hit: true;
  cache_id: string;
  original_question: string;
  response: string;
  suggestions: Suggestion[];
  score: number;              // 유사도 점수
  created_at: string;
  age_seconds: number;        // 캐시 나이
}
```

---

## 📎 부록

### A. TypeScript 타입 Export

```typescript
// types/analysis.ts
export type {
  DataBasket,
  BasketItem,
  ItemType,
  StockSnapshot,
  NewsSnapshot,
  FinancialSnapshot,
  MacroSnapshot,
  AnalysisSession,
  AnalysisMessage,
  Suggestion,
  GraphData,
  GraphNode,
  GraphEdge,
  SSEEvent,
  SSEEventPhase,
};
```

### B. JSON Schema (OpenAPI)

전체 OpenAPI 스펙은 `/api/v1/schema/` 에서 확인 가능합니다.

---

*SCREEN_DATA_STRUCTURE v1.0.0 - 2025-12-13*