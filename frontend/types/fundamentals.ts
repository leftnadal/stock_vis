// Other Fundamentals 관련 타입 정의

// 핵심 재무 지표
export interface KeyMetric {
  date: string;
  period: string;
  symbol: string;
  // Per Share Metrics
  revenuePerShare: number | null;
  netIncomePerShare: number | null;
  freeCashFlowPerShare: number | null;
  cashPerShare: number | null;
  bookValuePerShare: number | null;
  tangibleBookValuePerShare: number | null;
  // Valuation Metrics
  peRatio: number | null;
  pbRatio: number | null;
  priceToSalesRatio: number | null;
  pocfratio: number | null;
  pfcfRatio: number | null;
  evToSales: number | null;
  evToEbitda: number | null;
  enterpriseValue: number | null;
  marketCapitalization: number | null;
  // Leverage Metrics
  debtToEquity: number | null;
  debtToAssets: number | null;
  netDebtToEbitda: number | null;
  // Liquidity Metrics
  currentRatio: number | null;
  quickRatio: number | null;
  cashRatio: number | null;
  // Efficiency Metrics
  daysOfSalesOutstanding: number | null;
  daysOfInventoryOutstanding: number | null;
  operatingCycle: number | null;
  daysOfPayablesOutstanding: number | null;
  cashConversionCycle: number | null;
  // Growth Metrics
  revenueGrowth: number | null;
  epsgrowth: number | null;
  operatingIncomeGrowth: number | null;
  // Dividend Metrics
  dividendYield: number | null;
  payoutRatio: number | null;
}

// 재무 비율
export interface FinancialRatio {
  date: string;
  period: string;
  symbol: string;
  // Profitability Ratios
  grossProfitMargin: number | null;
  operatingProfitMargin: number | null;
  netProfitMargin: number | null;
  ebitPerRevenue: number | null;
  ebitdaPerRevenue: number | null;
  // Return Ratios
  returnOnEquity: number | null;
  returnOnAssets: number | null;
  returnOnCapitalEmployed: number | null;
  returnOnTangibleAssets: number | null;
  // Efficiency Ratios
  assetTurnover: number | null;
  inventoryTurnover: number | null;
  receivablesTurnover: number | null;
  payablesTurnover: number | null;
  // Coverage Ratios
  interestCoverage: number | null;
  cashFlowToDebtRatio: number | null;
  companyEquityMultiplier: number | null;
  // Operating Metrics
  operatingCashFlowPerShare: number | null;
  freeCashFlowPerShare: number | null;
  cashPerShare: number | null;
}

// DCF 평가
export interface DCFValuation {
  symbol: string;
  date: string;
  dcf: number;
  stockPrice: number;
  // Premium/Discount 계산
  premiumDiscount: number; // (stockPrice - dcf) / dcf * 100
}

// 투자 등급
export interface InvestmentRating {
  symbol: string;
  date: string;
  rating: string; // 'A+', 'A', 'B+', 'B', 'C+', 'C', 'D', 'F'
  ratingScore: number; // 0-100
  ratingRecommendation: string; // 'Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell'
  ratingDetailsDCFScore: number | null;
  ratingDetailsDCFRecommendation: string | null;
  ratingDetailsROEScore: number | null;
  ratingDetailsROERecommendation: string | null;
  ratingDetailsROAScore: number | null;
  ratingDetailsROARecommendation: string | null;
  ratingDetailsDEScore: number | null;
  ratingDetailsDERecommendation: string | null;
  ratingDetailsPEScore: number | null;
  ratingDetailsPERecommendation: string | null;
  ratingDetailsPBScore: number | null;
  ratingDetailsPBRecommendation: string | null;
}

// 전체 Fundamentals 데이터 (한 번에 조회)
export interface AllFundamentals {
  symbol: string;
  keyMetrics: KeyMetric[];
  ratios: FinancialRatio[];
  dcf: DCFValuation | null;
  rating: InvestmentRating | null;
}

// API 응답 타입
export interface FundamentalsResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}
