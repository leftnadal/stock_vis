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
  category?: string;
  sentiment_score: number | null;
  sentiment_source?: string;
  is_press_release?: boolean;
  entities?: NewsEntity[];
  entity_count?: number;
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
  reason?: string;  // AI 분석 이유
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
  period_days?: number;
  period_start?: string;
  period_end?: string;
  insights: StockInsight[];
  total_keywords: number;
  computation_time_ms?: number;
}

// ===== Phase A: Market Feed Types (Cold Start) =====

export interface BriefingKeyword extends DailyKeyword {
  news_count: number;
  headlines: { title: string; url: string }[];
}

export interface MarketFeedSector {
  name: string;
  return_pct: number;
  stock_count: number;
}

export interface MarketFeedMover {
  symbol: string;
  company_name: string;
  change_percent: number;
  sector: string;
}

export interface MarketFeedResponse {
  date: string;
  is_fallback: boolean;
  fallback_message: string | null;
  briefing: {
    keywords: BriefingKeyword[];
    total_news_count: number;
    llm_model: string | null;
  };
  market_context: {
    top_sectors: MarketFeedSector[];
    hot_movers: MarketFeedMover[];
  };
}

// ===== Phase B: Interest Types (Onboarding) =====

export interface InterestOption {
  interest_type: 'theme' | 'sector';
  value: string;
  display_name: string;
  sample_symbols: string[];
}

export interface InterestOptionsResponse {
  themes: InterestOption[];
  sectors: InterestOption[];
}

export interface UserInterest {
  id: number;
  interest_type: 'theme' | 'sector';
  value: string;
  display_name: string;
  auto_category_id: number | null;
  created_at: string;
}

// ===== Phase 4: ML Model Status Types =====

export interface MLModelMetrics {
  f1: number;
  precision: number;
  recall: number;
  accuracy: number;
}

export interface MLModelInfo {
  version: string | null;
  f1_score: number | null;
  status: string | null;
  trained_at: string | null;
  safety_gate: boolean | null;
}

export interface MLDeployedModel {
  version: string | null;
  f1_score: number | null;
  weights: Record<string, number> | null;
  deployed_at: string | null;
}

export interface MLModelHistoryItem {
  version: string;
  f1: number;
  precision: number;
  recall: number;
  gate_passed: boolean;
  status: string;
  trained_at: string;
}

export interface MLStatusResponse {
  latest_model: MLModelInfo | null;
  deployed_model: MLDeployedModel | null;
  recent_history: MLModelHistoryItem[];
  labeled_data_count: number;
  min_required: number;
  ready_for_training: boolean;
}

export interface ShadowComparison {
  period: string;
  total_articles: number;
  manual_selected: number;
  ml_selected: number;
  overlap: number;
  agreement_rate: number;
  only_manual_count?: number;
  only_ml_count?: number;
}

export interface MLShadowReportResponse {
  model_version?: string;
  deployment_status?: string;
  shadow_comparison?: ShadowComparison;
  metrics?: MLModelMetrics;
  weights?: Record<string, number>;
  safety_gate?: Record<string, unknown>;
  trained_at?: string;
  status?: string;
  message?: string;
}

// ===== Phase 4: News Events Types =====

export interface NewsEventImpact {
  symbol: string;
  direction: string;
  confidence: number;
  reason: string;
  chain_logic?: string;
}

export interface NewsEventData {
  article_id: string;
  title: string;
  source: string;
  importance_score: number;
  tier: string;
  published_at: string;
  direct_impacts: NewsEventImpact[];
  indirect_impacts: NewsEventImpact[];
}

export interface NewsEventSummary {
  total_events: number;
  bullish_count: number;
  bearish_count: number;
  avg_confidence: number;
  direct_count: number;
  indirect_count: number;
  opportunity_count: number;
}

export interface NewsEventsResponse {
  symbol: string;
  days: number;
  events: NewsEventData[];
  summary: NewsEventSummary;
}

// ===== Phase 5: ML Weekly Report Types =====

export interface MLWeeklyReportResponse {
  period: {
    start: string;
    end: string;
  };
  model_status: {
    deployed_version: string | null;
    deployed_f1: number | null;
    latest_version: string | null;
    latest_f1: number | null;
    latest_status: string | null;
  };
  performance_trend: {
    trend: 'improving' | 'stable' | 'declining';
    recent_f1_scores: { version: string; f1: number }[];
    gate_pass_rate: number;
  };
  llm_accuracy: {
    direction_accuracy: number;
    importance_accuracy: number;
    total_measured: number;
  };
  data_stats: {
    total_labeled: number;
    new_labeled_this_week: number;
    new_analyzed_this_week: number;
  };
  recommendations: string[];
  generated_at: string;
}

// ===== Phase 6: LightGBM Readiness Types =====

export interface LightGBMReadinessResponse {
  ready: boolean;
  conditions: {
    data_sufficient: {
      met: boolean;
      current: number;
      required: number;
    };
    lr_stagnation: {
      met: boolean;
      weeks_checked: number;
      f1_range: number | null;
    };
    feature_stability: {
      met: boolean;
      sector_coverage: number;
      required: number;
    };
  };
}
