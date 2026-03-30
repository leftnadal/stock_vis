/**
 * Overview 동적 레이어 타입 정의
 *
 * 백엔드 OverviewTabSerializer.get_dynamic_layers() 응답 구조.
 * - 데이터 전무: dynamic_layers = null
 * - 일부 존재: dynamic_layers = { category_scores: [...], news_summary: null, ... }
 */

export interface DynamicLayers {
  category_signals: CategorySignalData[] | null;
  news_summary: NewsSummaryData | null;
  sensitivity: SensitivityData | null;
  growth_stage: GrowthStageData | null;
  capital_dna: CapitalDNAData | null;
  narrative: NarrativeData | null;
}

export interface CategorySignalData {
  category: string;
  signal: 'green' | 'yellow' | 'red' | 'gray';
  signal_reason: string;
  metric_count: number;
  valid_metric_count: number;
}

export interface NewsSummaryData {
  event_count_30d: number;
  event_count_90d: number;
  avg_sentiment_30d: number | null;
  sentiment_trend: 'improving' | 'stable' | 'deteriorating' | '';
  has_regulatory_risk: boolean;
  has_exec_change: boolean;
  has_guidance_cut: boolean;
  recent_highlights: Array<{
    title: string;
    sentiment: number;
    event_type: string;
    date: string;
  }>;
}

export interface SensitivityData {
  rate_sensitivity: 'high' | 'medium' | 'low' | '';
  forex_sensitivity: 'high' | 'medium' | 'low' | '';
  commodity_sensitivity: 'high' | 'medium' | 'low' | '';
  regulation_type: string;
  is_regulated_industry: boolean;
  beta: number | null;
}

export interface GrowthStageData {
  stage: 'early_growth' | 'accelerating' | 'mature' | 'cash_cow' | 'turnaround' | 'declining' | '';
  revenue_cagr_3y: number | null;
  revenue_cagr_5y: number | null;
  fcf_trend: 'growing' | 'stable' | 'declining' | '';
  confidence: 'high' | 'medium' | 'low';
}

export interface CapitalDNAData {
  capital_type: 'heavy_investor' | 'balanced' | 'shareholder_first' | 'cash_hoarder' | 'aggressive_growth' | 'unknown' | '';
  rd_to_revenue: number | null;
  capex_to_revenue: number | null;
  dividend_payout: number | null;
  buyback_yield: number | null;
}

export interface NarrativeData {
  primary_narrative: string;
  theme_tags: string[];
  narrative_sentiment: 'positive' | 'mixed' | 'negative' | '';
  analyst_consensus: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell' | '';
  analyst_revision_trend: 'upgrading' | 'stable' | 'downgrading' | '';
}
