// News related types

export interface NewsEntity {
  symbol: string;
  entity_name: string;
  entity_type: string;
  sentiment_score: number | null;
}

export interface NewsArticle {
  id: string;
  url: string;
  title: string;
  summary: string;
  image_url: string | null;
  source: string;
  published_at: string;
  category: string;
  sentiment_score: number | null;
  sentiment_source: string;
  entities: NewsEntity[];
}

export interface NewsListItem {
  id: string;
  url: string;
  title: string;
  summary: string;
  image_url: string | null;
  source: string;
  published_at: string;
  sentiment_score: number | null;
  entity_count: number;
}

export interface SentimentHistory {
  date: string;
  avg_sentiment: number | null;
  news_count: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
}

export interface StockSentiment {
  symbol: string;
  total_articles: number;
  avg_sentiment: number | null;
  positive_ratio: number;
  negative_ratio: number;
  neutral_ratio: number;
  sentiment_trend: string;
  history: SentimentHistory[];
}

export interface TrendingStock {
  symbol: string;
  mention_count: number;
  avg_sentiment: number | null;
}

export interface StockNewsResponse {
  symbol: string;
  count: number;
  articles: NewsListItem[];
}

export interface TrendingNewsResponse {
  timeframe: string;
  count: number;
  stocks: TrendingStock[];
}

export type MarketNewsCategory = 'general' | 'forex' | 'crypto' | 'merger';

export interface MarketNewsResponse {
  category: string;
  count: number;
  articles: NewsListItem[];
}

// Phase 1: News Page Types
export type NewsSourceType = 'all' | 'finnhub' | 'marketaux';

export interface NewsSource {
  name: NewsSourceType;
  label: string;
  count: number;
}

export interface AllNewsResponse {
  source: string;
  category: string;
  days: number;
  total: number;
  count: number;
  offset: number;
  limit: number;
  has_more: boolean;
  articles: NewsListItem[];
}

export interface AllNewsParams {
  source?: NewsSourceType;
  category?: MarketNewsCategory | 'all';
  days?: number;
  limit?: number;
  offset?: number;
  refresh?: boolean;
}

// Phase 2: Daily Keyword Types
export interface DailyKeyword {
  text: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  related_symbols: string[];
  importance?: number;
}

export interface DailyNewsKeywordResponse {
  date: string;
  keywords: DailyKeyword[];
  total_news_count: number;
  sources: Record<string, number>;
  llm_model: string | null;
  status: 'pending' | 'completed' | 'failed' | 'not_found';
  generation_time_ms?: number;
  message?: string;
}

// Phase 3: Stock Recommendation Types (Legacy)
export interface StockRecommendation {
  symbol: string;
  company_name?: string;
  score: number;
  reasons: string[];
  avg_sentiment: number | null;
  price_change?: number;
  mention_count: number;
}

export interface RecommendationsResponse {
  date: string;
  recommendations: StockRecommendation[];
  total_keywords: number;
  computation_time_ms?: number;
  fallback?: boolean;
}

// ===== Phase 3.1: Stock Insights Types (Fact-Based) =====

/**
 * 키워드 언급 정보
 * 특정 키워드와 관련된 뉴스 헤드라인 및 감성 정보
 */
export interface KeywordMention {
  keyword: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  news_headline: string;
  news_source: string;
  published_at: string;  // ISO 8601 format
}

/**
 * 감성 분포
 * 긍정/부정/중립 뉴스 건수
 */
export interface SentimentDistribution {
  positive: number;
  negative: number;
  neutral: number;
  total: number;
}

/**
 * 가격 위치 정보
 * 52주 고가/저가 대비, 이동평균 대비 위치
 */
export interface PricePosition {
  current_price?: number;
  week_52_high?: number;
  week_52_low?: number;
  distance_from_52w_high?: number;  // percentage
  distance_from_52w_low?: number;   // percentage
  ma_50?: number;
  ma_200?: number;
  vs_ma_50?: number;   // percentage above/below MA50
  vs_ma_200?: number;  // percentage above/below MA200
}

/**
 * 밸류에이션 정보
 * PER, ROE, Beta, 애널리스트 목표가
 */
export interface Valuation {
  pe_ratio?: number;
  roe?: number;
  beta?: number;
  analyst_target?: number;
  analyst_upside?: number;  // percentage
}

/**
 * 애널리스트 레이팅
 */
export interface AnalystRatings {
  buy: number;
  hold: number;
  sell: number;
}

/**
 * 시장 데이터 (전문가용)
 * 가격 위치, 밸류에이션, 애널리스트 정보
 */
export interface MarketData {
  price_position?: PricePosition | null;
  valuation?: Valuation | null;
  analyst_ratings?: AnalystRatings | null;
}

/**
 * 종목 인사이트 (팩트 중심)
 * 추천 점수 대신 뉴스 언급 현황과 감성 분포를 제공
 */
export interface StockInsight {
  symbol: string;
  company_name?: string;
  keyword_mentions: KeywordMention[];
  sentiment_distribution: SentimentDistribution;
  market_data?: MarketData;
  total_news_count: number;
}

/**
 * 인사이트 API 응답
 */
export interface StockInsightsResponse {
  date: string;
  insights: StockInsight[];
  total_keywords: number;
  computation_time_ms?: number;
}
