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