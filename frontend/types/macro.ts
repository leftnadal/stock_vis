/**
 * Market Pulse 대시보드 타입 정의
 */

// ============================================================================
// Fear & Greed Index
// ============================================================================

export interface FearGreedIndex {
  value: number;
  rule_key: 'extreme_fear' | 'fear' | 'neutral' | 'greed' | 'extreme_greed';
  label: string;
  label_en?: string;
  color: string;
  bg_color?: string;
  message: string;
  action_hint?: string;
  vix?: VIXData;
  yield_spread?: YieldSpreadData;
  last_updated: string;
}

export interface VIXData {
  value: number;
  level: 'extreme_high' | 'high' | 'normal' | 'low';
  date: string;
}

export interface YieldSpreadData {
  spread: number | null;
  status: 'inverted' | 'flattening' | 'normal' | 'steep' | 'unknown';
  date: string | null;
}

// ============================================================================
// Interest Rates
// ============================================================================

export interface InterestRatesDashboard {
  fed_funds_rate: number | null;
  treasury_2y: number | null;
  treasury_10y: number | null;
  yield_spread: YieldSpreadData;
  yield_curve_status: YieldCurveStatus;
  yield_curve_data: YieldCurveDataPoint[];
  last_updated: string;
}

export interface YieldCurveStatus {
  rule_key: string;
  label: string;
  label_en?: string;
  color: string;
  bg_color?: string;
  message: string;
  historical_note?: string;
  typical_lag?: string;
}

export interface YieldCurveDataPoint {
  maturity: string;
  rate: number;
}

// ============================================================================
// Inflation & Employment
// ============================================================================

export interface InflationDashboard {
  inflation: InflationData;
  employment: EmploymentData;
  gdp: GDPData | null;
  last_updated: string;
}

export interface InflationData {
  cpi_yoy: number | null;
  core_cpi_yoy: number | null;
  pce_yoy: number | null;
  fed_target: number;
}

export interface EmploymentData {
  unemployment_rate: number | null;
  nfp_change: number | null;
  initial_claims: number | null;
}

export interface GDPData {
  real_gdp: number;
  qoq_growth: number;
  annualized_growth: number;
  date: string;
}

// ============================================================================
// Global Markets
// ============================================================================

export interface GlobalMarketsDashboard {
  indices: USIndices;
  global_indices: GlobalIndices;
  sectors: SectorPerformance;
  forex: Record<string, ForexData>;
  commodities: Record<string, CommodityData>;
  dxy: DXYData | null;
  vix: VIXData | null;
  last_updated: string;
}

export interface USIndices {
  sp500: IndexData | null;
  nasdaq: IndexData | null;
  dow: IndexData | null;
  russell2000: IndexData | null;
}

export interface GlobalIndices {
  ftse: IndexData | null;
  dax: IndexData | null;
  nikkei: IndexData | null;
  hangseng: IndexData | null;
}

export interface IndexData {
  name: string;
  price: number;
  change: number;
  change_percent: number;
  previous_close?: number;
  day_high?: number;
  day_low?: number;
  timestamp?: number;
}

export interface SectorPerformance {
  sectors: Record<string, SectorData>;
  best_performer: [string, SectorData] | null;
  worst_performer: [string, SectorData] | null;
}

export interface SectorData {
  name: string;
  price: number;
  change_percent: number;
  ytd_return?: number;
}

export interface ForexData {
  name: string;
  price: number;
  change: number;
  change_percent: number;
}

export interface CommodityData {
  name: string;
  price: number;
  change: number;
  change_percent: number;
}

export interface DXYData {
  value: number;
  change: number;
  change_percent: number;
  timestamp?: number;
}

// ============================================================================
// Economic Calendar
// ============================================================================

export interface EconomicCalendar {
  events_by_date: Record<string, EconomicEventItem[]>;
  total_count: number;
  from_date: string;
  to_date: string;
  last_updated: string;
}

export interface EconomicEventItem {
  time: string;
  event: string;
  country: string;
  impact: 'High' | 'Medium' | 'Low';
  actual: string | null;
  previous: string | null;
  estimate: string | null;
}

// ============================================================================
// Combined Dashboard
// ============================================================================

export interface MarketPulseDashboard {
  fear_greed: FearGreedIndex;
  interest_rates: InterestRatesDashboard;
  economy: InflationDashboard;
  global_markets: GlobalMarketsDashboard;
  calendar: EconomicCalendar;
  last_updated: string;
}
