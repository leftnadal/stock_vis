// 주식 관련 타입 정의

// MVP용 간소화된 주식 데이터
export interface StockBasic {
  symbol: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  changePercent: string | null;
  marketCap: number;
}

// 주식 상세 정보 (RAG용)
export interface StockDetail {
  basic: {
    symbol: string;
    name: string;
    sector: string;
    industry: string;
    description: string;
    exchange: string;
  };
  price: {
    current: number;
    change: number;
    changePercent: string | null;
    high52Week: number;
    low52Week: number;
  };
  valuation: {
    marketCap: number;
    peRatio: number;
    eps: number;
    dividendYield: number;
    beta: number;
  };
  keyMetrics: {
    profitMargin: number;
    returnOnEquity: number;
    returnOnAssets: number;
  };
  financials?: {
    revenue: number;
    netIncome: number;
    fiscalYear: number;
  };
}

// API 응답 타입
export interface StockListResponse {
  mode: 'summary' | 'full';
  count: number;
  data: StockBasic[];
}

export interface StockDetailResponse {
  mode: 'summary' | 'full';
  symbol: string;
  data: StockDetail;
}

// RAG 컨텍스트
export interface RAGContext {
  symbol: string;
  mode: 'summary' | 'full';
  context: string;
  tokenCount: number;
}

// Corporate Actions (기업 행동)
export type CorporateActionType = 'reverse_split' | 'split' | 'spinoff' | 'dividend';

export interface CorporateAction {
  type: CorporateActionType;
  date: string;
  display: string; // 표시 텍스트 (예: "1:10", "2:1", "$5.00")
  description?: string; // 추가 설명
  ratio?: number; // 분할 비율 (split/reverse_split)
  amount?: number; // 배당 금액 (dividend)
}

export interface StockWithActions extends StockBasic {
  actions?: CorporateAction[];
}

export interface PriceDataPoint {
  date: string;
  close: number;
  volume?: number;
  action?: CorporateAction; // 해당 날짜에 발생한 corporate action
}