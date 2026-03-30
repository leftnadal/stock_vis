/**
 * 1차 검증 TypeScript 타입 정의
 * 백엔드 API 응답 구조 (설계서 섹션 5.2)
 */

// ── Summary API ──

export interface ValidationSummary {
  symbol: string;
  company_name: string;
  data_fiscal_year: number;
  data_freshness: string | null;
  category_signals: CategorySignal[];
  summary_text: string;
  summary_source: 'rule' | 'llm';
  peer_info: PeerInfo | null;
  industry_position: IndustryPosition;
  // error cases
  error?: 'not_in_universe' | 'no_data';
  message?: string;
}

export interface CategorySignal {
  category: string;
  display_name: string;
  signal: 'green' | 'yellow' | 'red' | 'gray';
  description: string;
  metric_count: number;
  signal_reason: string;
}

export interface PeerInfo {
  industry: string;
  peer_count: number;
  confidence: string;
  benchmark_basis: 'industry_size' | 'industry' | 'sector';
  size_bucket: 'mega' | 'large' | 'mid' | 'small';
  basis_description: string;
  top_peers: string[];
  industry_leader: IndustryLeader | null;
}

export interface IndustryLeader {
  symbol: string;
  name: string;
  market_cap: number | null;
}

export interface IndustryPosition {
  ranks: IndustryRank[];
}

export interface IndustryRank {
  metric: string;
  display_name: string;
  rank: number;
  total: number;
  value: number | null;
}

// ── Metrics API ──

export interface ValidationMetricsResponse {
  symbol: string;
  categories: CategoryMetrics[];
}

export interface CategoryMetrics {
  category: string;
  display_name: string;
  display_name_en: string;
  signal: 'green' | 'yellow' | 'red' | 'gray';
  description: string;
  metrics: MetricData[];
}

export interface MetricData {
  metric_code: string;
  display_name: string;
  display_name_en: string;
  unit: 'ratio' | 'multiple' | 'days' | 'pct' | 'percent_point' | 'years' | 'flag';
  higher_is_better: boolean;
  current: MetricCurrent | null;
  benchmark: MetricBenchmark | null;
  history: ChartDataPoint[];
  trend: 'improving' | 'declining' | 'stable' | '';
  interpretation: string;
  interpretation_source: 'rule' | 'llm';
}

export interface MetricCurrent {
  value: number | null;
  fiscal_year: number;
  value_status: 'normal' | 'missing' | 'not_applicable' | 'unstable' | 'low_confidence';
}

export interface MetricBenchmark {
  basis: 'industry_size' | 'industry' | 'sector';
  confidence: 'high' | 'medium' | 'low' | 'limited';
  median: number | null;
  p25: number | null;
  p75: number | null;
  percentile_rank: number | null;
  rank: number | null;
  total: number | null;
}

export interface ChartDataPoint {
  fiscal_year: number;
  company_value: number | null;
  peer_median: number | null;
  peer_p25: number | null;
  peer_p75: number | null;
}

// ── Leader Comparison API ──

export interface LeaderComparison {
  symbol: string;
  fiscal_year: number;
  leader: IndustryLeader;
  comparisons: LeaderMetricComparison[];
  summary_metrics: LeaderMetricComparison[];
  total_compared: number;
  advantages_count: number;
  summary: string;
  summary_source: 'rule' | 'llm';
  // error cases
  error?: 'insufficient_peers' | 'no_leader' | 'no_data';
  message?: string;
}

export interface LeaderMetricComparison {
  metric_code: string;
  display_name: string;
  category: string;
  company_value: number;
  leader_value: number;
  gap: number;
  is_advantage: boolean;
}
