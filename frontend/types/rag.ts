// RAG 바구니 관련 타입

export interface BasketItem {
  id: number;
  item_type: string;  // 'overview', 'price', 'financial_summary', 'financial_full', 'indicator', 'news', 'macro'
  reference_id: string;
  title: string;
  subtitle?: string;
  data_snapshot: Record<string, any>;
  snapshot_date: string;
  data_units: number;
  added_at: string;
  // 레거시 필드 (하위 호환성)
  type?: 'stock_data' | 'financial' | 'metric' | 'url' | 'text';
  content?: any;
  source?: string;
  symbol?: string;
}

export interface Basket {
  id: number;
  user: number;
  name: string;
  description?: string;
  items: BasketItem[];
  items_count: number;
  current_units: number;
  remaining_units: number;
  max_units: number;
  can_add_item: boolean;
  created_at: string;
  updated_at: string;
}

export interface BasketState {
  items: BasketItem[];
  isOpen: boolean;
}

// 세션 관련 타입
export interface Session {
  id: number;
  user: number;
  basket: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  session: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
  latency_ms?: number;
}

// SSE 스트리밍 관련 타입
export interface SSEEvent {
  phase: 'cache_check' | 'cache_hit' | 'preparing' | 'context_ready' | 'analyzing' | 'streaming' | 'complete' | 'error' | 'basket_cleared';
  message?: string;
  chunk?: string;
  data?: CompleteData;
  error?: {
    code: string;
    message: string;
  };
  // Phase 3: 복잡도 정보 (analyzing 단계에서 제공)
  complexity?: 'simple' | 'moderate' | 'complex';
  complexity_score?: number;
}

export interface CacheInfo {
  cache_id?: string;
  similarity_score?: number;
  entity_match_score?: number;
  hit_count?: number;
}

export interface CompleteData {
  content: string;
  suggestions: Suggestion[];
  basket_actions?: BasketAction[];
  usage: {
    input_tokens: number;
    output_tokens: number;
    cached?: boolean;
    cost_usd?: number;  // Phase 3: 비용 정보
  };
  cache_info?: CacheInfo;
  cache_id?: string;
  latency_ms: number;
  // Phase 3: 복잡도 정보
  complexity?: 'simple' | 'moderate' | 'complex';
  complexity_score?: number;
}

export interface Suggestion {
  symbol: string;
  reason: string;
}

export interface BasketAction {
  symbol: string;
  name: string;
  recommended: string[];
  available: string[];
}

// LLM 요청/응답 타입 (레거시)
export interface AdvisorRequest {
  prompt: string;
  context: BasketItem[];
  mode: 'summary' | 'detailed';
}

export interface AdvisorResponse {
  advice: string;
  recommendations: Recommendation[];
  timestamp: Date;
}

export interface Recommendation {
  action: 'buy' | 'sell' | 'hold' | 'rebalance';
  symbol: string;
  quantity?: number;
  reason: string;
}

// 데이터 타입별 정보
export const DATA_TYPE_INFO: Record<string, { label: string; units: number; icon: string }> = {
  overview: { label: '기본 정보', units: 5, icon: '📋' },
  price: { label: '현재 주가', units: 5, icon: '💰' },
  financial_summary: { label: '재무제표 (요약)', units: 15, icon: '📊' },
  financial_full: { label: '재무제표 (전체)', units: 45, icon: '📈' },
  indicator: { label: '기술적 지표', units: 5, icon: '📉' },
  news: { label: '최근 뉴스', units: 3, icon: '📰' },
  macro: { label: '거시경제', units: 10, icon: '🌍' },
};