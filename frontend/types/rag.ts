// RAG 바구니 관련 타입

export interface BasketItem {
  id: string;
  type: 'stock_data' | 'financial' | 'metric' | 'url' | 'text';
  title: string;
  content: any;
  source: string;
  addedAt: Date;
}

export interface BasketState {
  items: BasketItem[];
  isOpen: boolean;
}

// LLM 요청/응답 타입
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