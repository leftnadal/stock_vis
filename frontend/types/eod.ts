// === Market Summary ===
export interface MarketSummary {
  sp500_change: number;
  qqq_change: number;
  vix: number;
  vix_regime: 'normal' | 'elevated' | 'high_vol';
  total_signals: number;
  bullish_count: number;
  bearish_count: number;
  stocks_with_signals: number;
  stock_universe: number;
  headline: string;
}

// === News Context ===
export type NewsMatchType = 'symbol_today' | 'symbol_7d' | 'symbol_30d' | 'industry_7d' | 'profile';
export type NewsConfidence = 'very_high' | 'high' | 'medium' | 'low' | 'context' | 'info';

export interface NewsContext {
  headline: string;
  source: string;
  url: string;
  match_type: NewsMatchType;
  confidence: NewsConfidence;
  age_days: number;
}

// === Signal Stock ===
export interface SignalStock {
  symbol: string;
  company_name: string;
  sector: string;
  industry: string;
  close_price: number;
  change_percent: number;
  signal_value: number;
  signal_label: string;
  signal_direction: string;
  news_context: NewsContext;
  mini_chart_20d: number[];
  chain_sight_cta: boolean;
  composite_score: number;
  market_cap: number | null;
  volume: number;
  dollar_volume: number;
}

// === Signal Card ===
export interface SignalCard {
  id: string;
  category: SignalCategory;
  color: string;
  title: string;
  count: number;
  description_ko: string;
  education_tip: string;
  education_risk: string;
  preview_stocks: SignalStock[];
  more_count: number;
  chain_sight_sectors: string[];
  rank_by_volume: (string | SignalStock)[];
  rank_by_return: (string | SignalStock)[];
  rank_by_market_cap: (string | SignalStock)[];
}

// === Pipeline Meta ===
export interface PipelineMeta {
  duration_seconds: number;
  pipeline_version: string;
  run_id: string;
  ingest_quality: {
    total_received: number;
    sector_null_pct: number;
    volume_zero_pct: number;
    dollar_vol_filtered: number;
  };
}

// === Recommendation (추천 캐러셀, D-P1-REC-CONTRACT) ===
export type RecommendationConfidence = 'high' | 'medium' | 'low';

// LLM 채움 전 placeholder 3키(D-P1-CAROUSEL). additive-within: 값만 채워짐.
export interface RecommendationPerspectives {
  technical: string | null;
  fundamental: string | null;
  news_context: string | null;
}

export interface Recommendation {
  rank: number;
  ticker: string;
  company_name: string;
  signal_tag: string;
  confidence: RecommendationConfidence;
  conf_ver: number;
  composite_score: number; // 부호 보존: 양=매수 우위, 음=매도/회피 우위
  thesis: string | null;
  perspectives: RecommendationPerspectives;
  risk: string | null;
}

// === Dashboard Data (dashboard.json 전체) ===
export interface EODDashboardData {
  generated_at: string;
  trading_date: string;
  is_stale: boolean;
  market_summary: MarketSummary;
  signal_cards: SignalCard[];
  pipeline_meta: PipelineMeta;
  recommendations?: Recommendation[]; // 하위호환: 부재 시 캐러셀 생략
}

// === Category & Colors ===
export type SignalCategory = 'momentum' | 'volume' | 'breakout' | 'reversal' | 'relation' | 'technical';

export const SIGNAL_CATEGORY_COLORS: Record<SignalCategory, string> = {
  momentum: '#F0883E',
  volume: '#58A6FF',
  breakout: '#3FB950',
  reversal: '#A371F7',
  relation: '#A371F7',
  technical: '#8B949E',
};

export const SIGNAL_CATEGORY_LABELS: Record<SignalCategory, string> = {
  momentum: '모멘텀',
  volume: '거래량',
  breakout: '돌파',
  reversal: '반전',
  relation: '상대강도',
  technical: '기술적',
};

// === Sort Options ===
export type SortOption = 'volume' | 'return' | 'market_cap';

// === Card Detail Data (cards/{signal_id}.json) ===
export interface SignalCardDetail {
  signal_id: string;
  category: SignalCategory;
  title: string;
  total_count: number;
  stocks_by_score: SignalStock[];
  stocks_by_volume: SignalStock[];
  stocks_by_return: SignalStock[];
  stocks_by_market_cap: SignalStock[];
  sector_distribution: string[];
}
