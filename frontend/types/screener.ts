/**
 * Screener Types
 */

// Market Breadth
export interface MarketBreadthSignalInterpretation {
  title: string;
  description: string;
  color: string;
  emoji: string;
}

export type BreadthSignal =
  | 'strong_bullish'
  | 'bullish'
  | 'neutral'
  | 'bearish'
  | 'strong_bearish';

export interface MarketIndex {
  name: string;
  symbol: string;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  error?: string;
}

export interface MarketIndices {
  sp500: MarketIndex;
  nasdaq: MarketIndex;
  dow: MarketIndex;
}

export interface MethodologyAccuracy {
  direction: string;
  exact_count: string;
  volume: string;
}

export interface InterpretationGuide {
  strong_bullish: string;
  bullish: string;
  neutral: string;
  bearish: string;
  strong_bearish: string;
}

export interface MarketBreadthMethodology {
  sample_size: number;
  total_market: number;
  sample_rate: string;
  data_source: string;
  accuracy: MethodologyAccuracy;
  interpretation_guide: InterpretationGuide;
  limitations: string[];
}

export interface MarketBreadthData {
  date: string;
  advancing_count: number;
  declining_count: number;
  advance_decline_ratio: number;
  breadth_signal: BreadthSignal;
  signal_interpretation: MarketBreadthSignalInterpretation;
  indices?: MarketIndices;
  methodology?: MarketBreadthMethodology;
}

export interface MarketBreadthResponse {
  success: boolean;
  data: MarketBreadthData;
}

// Sector Heatmap
export interface SectorPerformance {
  sector: string;
  name?: string;
  name_ko: string;
  return_pct: number | string;
  market_cap: number;
  stock_count: number;
  etf_symbol: string;
  color: string;
}

export interface SectorHeatmapResponse {
  success: boolean;
  data: {
    date: string;
    sectors: SectorPerformance[];
  };
}

// Screener Presets
export type PresetType = 'instant' | 'enhanced';

export interface ScreenerPreset {
  id: number;
  name: string;
  description_ko: string;
  category: string;
  icon: string;
  filters_json: Record<string, any>;
  use_count: number;
  is_system: boolean;
  preset_type?: PresetType;  // instant: FMP 직접 지원, enhanced: 추가 API 필요 (PE/ROE/EPS 등)
  created_by?: number;
  created_at?: string;
  updated_at?: string;
  share_code?: string;  // Phase 2.1: 공유 코드
  share_url?: string;    // Phase 2.1: 공유 URL
  expires_at?: string;   // Phase 2.1: 공유 만료일
}

export interface ScreenerPresetsResponse {
  success: boolean;
  data: {
    count: number;
    presets: ScreenerPreset[];
  };
}

export interface CreatePresetPayload {
  name: string;
  description_ko: string;
  category?: string;
  icon?: string;
  filters_json: Record<string, any>;
}

// Advanced Screener
export interface ScreenerFilters {
  // 기본 필터
  min_market_cap?: number;
  max_market_cap?: number;
  min_price?: number;
  max_price?: number;
  min_volume?: number;
  max_volume?: number;
  sectors?: string[];
  sector?: string;  // 단일 섹터 (URL 파라미터용)
  exchanges?: string[];

  // URL 파라미터 호환 (레거시)
  per_min?: number;
  per_max?: number;
  roe_min?: number;
  market_cap_min?: number;
  market_cap_max?: number;
  beta_min?: number;
  beta_max?: number;
  dividend_min?: number;
  volume_min?: number;

  // 밸류에이션
  min_pe?: number;
  max_pe?: number;
  min_pb?: number;
  max_pb?: number;
  min_ps?: number;
  max_ps?: number;
  min_pcf?: number;
  max_pcf?: number;

  // 수익성
  min_roe?: number;
  max_roe?: number;
  min_roa?: number;
  max_roa?: number;
  min_net_margin?: number;
  max_net_margin?: number;

  // 성장성
  min_revenue_growth?: number;
  max_revenue_growth?: number;
  min_eps_growth?: number;
  max_eps_growth?: number;

  // 재무건전성
  min_current_ratio?: number;
  max_current_ratio?: number;
  min_debt_to_equity?: number;
  max_debt_to_equity?: number;

  // 배당
  min_dividend_yield?: number;
  max_dividend_yield?: number;

  // 기술적 지표
  min_rsi?: number;
  max_rsi?: number;
  min_beta?: number;
  max_beta?: number;

  // Market Movers 지표
  rvol_min?: number;
  trend_strength_min?: number;
  sector_alpha_min?: number;
  volatility_pct_min?: number;

  // 추가 필터 (프리셋용)
  rsi_min?: number;
  rsi_max?: number;
  debt_equity_max?: number;
  eps_growth_min?: number;
  eps_growth_max?: number;
  revenue_growth_min?: number;
  revenue_growth_max?: number;
  current_ratio_min?: number;
  change_percent_min?: number;
  change_percent_max?: number;
}

export interface ScreenerStock {
  symbol: string;
  name?: string;
  company_name?: string;
  sector?: string;
  industry?: string;
  market_cap?: number;
  price?: number;
  change?: number;
  change_percent?: number | string;
  changes_percentage?: number;
  previous_close?: number;
  day_high?: number;
  day_low?: number;
  open_price?: number;
  volume?: number;
  pe_ratio?: number;
  pe?: number;
  pb_ratio?: number;
  dividend_yield?: number;
  last_annual_dividend?: number;
  roe?: number;
  eps?: number;
  revenue_growth?: number;
  eps_growth?: number;
  debt_to_equity?: number;
  current_ratio?: number;
  rsi?: number;
  beta?: number;
  exchange?: string;
  exchange_short_name?: string;
  country?: string;
  formatted_market_cap?: string;
  formatted_volume?: string;
  is_etf?: boolean;
  is_fund?: boolean;
  is_actively_trading?: boolean;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ScreenerResponse {
  success: boolean;
  data: {
    stocks: ScreenerStock[];
    meta: PaginationMeta;
    filters_applied: ScreenerFilters;
  };
}

// Pagination Props
export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalCount: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}

// ===========================================
// 프리셋 중복 적용 (캐스케이딩 필터) 관련 타입
// ===========================================

// 필터 충돌 유형
export type FilterConflictType =
  | 'range_narrowing'    // 2차가 1차 범위 좁힘 (OK)
  | 'range_conflict'     // 2차가 1차와 충돌 (경고, 1차 유지)
  | 'value_override'     // 이산값 충돌 (경고, 1차 유지)
  | 'compatible';        // 충돌 없음

// 필터 타입 (충돌 판단용)
export type FilterType = 'range_max' | 'range_min' | 'discrete' | 'array';

// 필터 메타데이터
export interface FilterMetadata {
  type: FilterType;
  labelKo: string;
  unit?: string;
  pairKey?: string;  // range_min/max 쌍일 때 상대 키
}

// 충돌 정보
export interface FilterConflict {
  filterKey: string;
  filterLabel: string;
  firstPresetValue: number | string | string[];
  secondPresetValue: number | string | string[];
  conflictType: FilterConflictType;
  resolution: string;  // 해결 설명
  firstPresetName: string;
  secondPresetName: string;
}

// 결합 결과
export interface CombinedPresetResult {
  effectiveFilters: ScreenerFilters;
  conflicts: FilterConflict[];
  hasWarnings: boolean;
  appliedPresetIds: number[];
  filterSources: Record<string, number>;  // 필터별 출처 프리셋 ID
}

// 필터 메타데이터 정의 (충돌 판단용)
export const FILTER_METADATA: Record<string, FilterMetadata> = {
  // PER 관련
  per_max: { type: 'range_max', labelKo: 'PER 최대', pairKey: 'per_min' },
  per_min: { type: 'range_min', labelKo: 'PER 최소', pairKey: 'per_max' },

  // ROE 관련
  roe_min: { type: 'range_min', labelKo: 'ROE 최소', unit: '%', pairKey: 'roe_max' },
  roe_max: { type: 'range_max', labelKo: 'ROE 최대', unit: '%', pairKey: 'roe_min' },

  // 시가총액
  market_cap_min: { type: 'range_min', labelKo: '시가총액 최소', unit: '$B', pairKey: 'market_cap_max' },
  market_cap_max: { type: 'range_max', labelKo: '시가총액 최대', unit: '$B', pairKey: 'market_cap_min' },

  // 배당
  dividend_min: { type: 'range_min', labelKo: '배당률 최소', unit: '%', pairKey: 'dividend_max' },
  dividend_max: { type: 'range_max', labelKo: '배당률 최대', unit: '%', pairKey: 'dividend_min' },

  // 거래량
  volume_min: { type: 'range_min', labelKo: '거래량 최소', unit: 'M', pairKey: 'volume_max' },
  volume_max: { type: 'range_max', labelKo: '거래량 최대', unit: 'M', pairKey: 'volume_min' },

  // 베타
  beta_min: { type: 'range_min', labelKo: '베타 최소', pairKey: 'beta_max' },
  beta_max: { type: 'range_max', labelKo: '베타 최대', pairKey: 'beta_min' },

  // 섹터 (이산값)
  sector: { type: 'discrete', labelKo: '섹터' },

  // RVOL (Market Movers)
  rvol_min: { type: 'range_min', labelKo: 'RVOL 최소', unit: 'x' },

  // Trend Strength
  trend_strength_min: { type: 'range_min', labelKo: '추세 강도 최소' },

  // Sector Alpha
  sector_alpha_min: { type: 'range_min', labelKo: '섹터 알파 최소', unit: '%' },

  // RSI
  rsi_min: { type: 'range_min', labelKo: 'RSI 최소', pairKey: 'rsi_max' },
  rsi_max: { type: 'range_max', labelKo: 'RSI 최대', pairKey: 'rsi_min' },

  // 변동성
  volatility_pct_min: { type: 'range_min', labelKo: '변동성 백분위 최소', unit: '%ile' },

  // 재무비율
  debt_equity_max: { type: 'range_max', labelKo: '부채비율 최대' },

  // EPS 성장률
  eps_growth_min: { type: 'range_min', labelKo: 'EPS 성장률 최소', unit: '%', pairKey: 'eps_growth_max' },
  eps_growth_max: { type: 'range_max', labelKo: 'EPS 성장률 최대', unit: '%', pairKey: 'eps_growth_min' },

  // 매출 성장률
  revenue_growth_min: { type: 'range_min', labelKo: '매출 성장률 최소', unit: '%', pairKey: 'revenue_growth_max' },
  revenue_growth_max: { type: 'range_max', labelKo: '매출 성장률 최대', unit: '%', pairKey: 'revenue_growth_min' },

  // 유동비율
  current_ratio_min: { type: 'range_min', labelKo: '유동비율 최소' },

  // 변동률
  change_percent_min: { type: 'range_min', labelKo: '변동률 최소', unit: '%', pairKey: 'change_percent_max' },
  change_percent_max: { type: 'range_max', labelKo: '변동률 최대', unit: '%', pairKey: 'change_percent_min' },
};


// ===========================================
// Alert System Types (Phase 1)
// ===========================================

export type AlertType =
  | 'filter_match'
  | 'price_target'
  | 'volume_spike'
  | 'ai_signal'
  | 'new_high'
  | 'new_low';

export interface ScreenerAlert {
  id: number;
  name: string;
  description: string;
  preset?: number;
  preset_name?: string;
  filters_json: ScreenerFilters;
  alert_type: AlertType;
  target_count?: number;
  target_symbols: string[];
  is_active: boolean;
  cooldown_hours: number;
  last_triggered_at?: string;
  trigger_count: number;
  notify_in_app: boolean;
  notify_email: boolean;
  notify_push: boolean;
  can_trigger: boolean;
  cooldown_remaining_hours: number;
  created_at: string;
  updated_at: string;
}

export interface CreateAlertPayload {
  name: string;
  description?: string;
  preset?: number;
  filters_json?: ScreenerFilters;
  alert_type?: AlertType;
  target_count?: number;
  target_symbols?: string[];
  cooldown_hours?: number;
  notify_in_app?: boolean;
  notify_email?: boolean;
  notify_push?: boolean;
}

export interface AlertHistory {
  id: number;
  alert: number;
  alert_name: string;
  triggered_at: string;
  matched_count: number;
  matched_symbols: string[];
  snapshot: Record<string, any>;
  status: 'sent' | 'failed' | 'skipped';
  error_message?: string;
  read_at?: string;
  dismissed: boolean;
  is_read?: boolean;
}

export interface AlertsResponse {
  success: boolean;
  data: {
    count: number;
    alerts: ScreenerAlert[];
  };
}

export interface AlertHistoryResponse {
  success: boolean;
  data: {
    count: number;
    history: AlertHistory[];
    unread_count: number;
  };
}


// ===========================================
// CSV Export Types (Phase 1)
// ===========================================

export interface ExportPayload {
  filters: ScreenerFilters;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  max_rows?: number;
}

export interface MoversExportPayload {
  type: 'gainers' | 'losers' | 'actives';
  date?: string;
}


// ===========================================
// Preset Sharing Types (Phase 2.1)
// ===========================================

export interface SharedPresetData {
  id: number;
  name: string;
  description_ko: string;
  category: string;
  filters_json: ScreenerFilters;
  created_by_username: string;
  created_at: string;
  share_code: string;
  expires_at: string;
}

export interface SharePresetResponse {
  success: boolean;
  data: {
    share_code: string;
    share_url: string;
    expires_at: string;
  };
}

export interface GetSharedPresetResponse {
  success: boolean;
  data: SharedPresetData;
}

export interface ImportPresetPayload {
  custom_name?: string;
}

export interface ImportPresetResponse {
  success: boolean;
  data: ScreenerPreset;
}


// ===========================================
// Chain Sight Types (Phase 2.2)
// ===========================================

export interface ChainStockMetrics {
  sector?: string;
  industry?: string;
  pe?: number;
  roe?: number;
  market_cap?: number;
  profit_margin?: number;
}

export interface ChainStock {
  symbol: string;
  company_name?: string;
  reason: string;
  similarity: number;
  change_percent?: number;
  metrics?: ChainStockMetrics;
}

export interface ChainSightData {
  sector_peers: ChainStock[];
  fundamental_similar: ChainStock[];
  ai_insights?: string;
  chains_count: number;
}

export interface ChainSightResponse {
  success: boolean;
  data: ChainSightData;
}


// ===========================================
// Investment Thesis Types (Phase 2.3)
// ===========================================

export interface InvestmentThesis {
  id: number;
  title: string;
  summary: string;
  key_metrics: string[];
  top_picks: string[];
  risks: string[];
  share_code?: string;
  created_at: string;
}

export interface GenerateThesisPayload {
  stocks: ScreenerStock[];
  filters: ScreenerFilters;
  user_notes?: string;
}

export interface ThesisResponse {
  success: boolean;
  data: InvestmentThesis;
  warning?: string;  // LLM 실패 시 폴백 테제 경고
}

export interface MyThesesResponse {
  success: boolean;
  data: {
    count: number;
    theses: InvestmentThesis[];
  };
}


// ===========================================
// Filter Category Types (AdvancedFilterPanel)
// ===========================================

export type FilterCategory =
  | 'price'
  | 'volume'
  | 'fundamental'
  | 'technical'
  | 'dividend'
  | 'market_movers'
  | 'other';

export interface FilterDefinition {
  id: string;
  label: string;
  labelKo: string;
  category: FilterCategory;
  type: 'range' | 'select' | 'multi_select' | 'boolean';
  unit?: string;
  minValue?: number;
  maxValue?: number;
  step?: number;
  options?: { value: string; label: string }[];
  description?: string;
  descriptionKo?: string;
  isPopular?: boolean;
}

export const FILTER_CATEGORIES: { id: FilterCategory; label: string; labelKo: string }[] = [
  { id: 'price', label: 'Price', labelKo: '가격' },
  { id: 'volume', label: 'Volume', labelKo: '거래량' },
  { id: 'fundamental', label: 'Fundamental', labelKo: '펀더멘탈' },
  { id: 'technical', label: 'Technical', labelKo: '기술적' },
  { id: 'dividend', label: 'Dividend', labelKo: '배당' },
  { id: 'market_movers', label: 'Market Movers', labelKo: 'MM 지표' },
];

export const ADVANCED_FILTERS: FilterDefinition[] = [
  // Price
  { id: 'min_price', label: 'Min Price', labelKo: '최소 가격', category: 'price', type: 'range', unit: '$', minValue: 0, maxValue: 10000, step: 1 },
  { id: 'max_price', label: 'Max Price', labelKo: '최대 가격', category: 'price', type: 'range', unit: '$', minValue: 0, maxValue: 10000, step: 1 },
  { id: 'market_cap_min', label: 'Min Market Cap', labelKo: '최소 시가총액', category: 'price', type: 'range', unit: '$B', minValue: 0, maxValue: 3000, step: 1, isPopular: true },
  { id: 'market_cap_max', label: 'Max Market Cap', labelKo: '최대 시가총액', category: 'price', type: 'range', unit: '$B', minValue: 0, maxValue: 3000, step: 1 },

  // Volume
  { id: 'volume_min', label: 'Min Volume', labelKo: '최소 거래량', category: 'volume', type: 'range', unit: 'M', minValue: 0, maxValue: 1000, step: 1 },
  { id: 'rvol_min', label: 'Min RVOL', labelKo: '최소 RVOL', category: 'market_movers', type: 'range', unit: 'x', minValue: 0, maxValue: 10, step: 0.1, descriptionKo: '거래량 배수 (당일/20일 평균)' },

  // Fundamental - Valuation
  { id: 'per_min', label: 'Min P/E', labelKo: '최소 PER', category: 'fundamental', type: 'range', minValue: 0, maxValue: 500, step: 1 },
  { id: 'per_max', label: 'Max P/E', labelKo: '최대 PER', category: 'fundamental', type: 'range', minValue: 0, maxValue: 500, step: 1, isPopular: true },
  { id: 'min_pb', label: 'Min P/B', labelKo: '최소 PBR', category: 'fundamental', type: 'range', minValue: 0, maxValue: 50, step: 0.1 },
  { id: 'max_pb', label: 'Max P/B', labelKo: '최대 PBR', category: 'fundamental', type: 'range', minValue: 0, maxValue: 50, step: 0.1 },

  // Fundamental - Profitability
  { id: 'roe_min', label: 'Min ROE', labelKo: '최소 ROE', category: 'fundamental', type: 'range', unit: '%', minValue: -100, maxValue: 200, step: 1, isPopular: true },
  { id: 'min_roa', label: 'Min ROA', labelKo: '최소 ROA', category: 'fundamental', type: 'range', unit: '%', minValue: -100, maxValue: 100, step: 1 },
  { id: 'min_net_margin', label: 'Min Net Margin', labelKo: '최소 순이익률', category: 'fundamental', type: 'range', unit: '%', minValue: -100, maxValue: 100, step: 1 },

  // Fundamental - Growth
  { id: 'min_revenue_growth', label: 'Min Revenue Growth', labelKo: '최소 매출 성장', category: 'fundamental', type: 'range', unit: '%', minValue: -100, maxValue: 500, step: 1 },
  { id: 'eps_growth_min', label: 'Min EPS Growth', labelKo: '최소 EPS 성장', category: 'fundamental', type: 'range', unit: '%', minValue: -100, maxValue: 500, step: 1 },

  // Fundamental - Financial Health
  { id: 'debt_equity_max', label: 'Max D/E Ratio', labelKo: '최대 부채비율', category: 'fundamental', type: 'range', minValue: 0, maxValue: 10, step: 0.1 },
  { id: 'min_current_ratio', label: 'Min Current Ratio', labelKo: '최소 유동비율', category: 'fundamental', type: 'range', minValue: 0, maxValue: 10, step: 0.1 },

  // Dividend
  { id: 'dividend_min', label: 'Min Dividend Yield', labelKo: '최소 배당수익률', category: 'dividend', type: 'range', unit: '%', minValue: 0, maxValue: 20, step: 0.1, isPopular: true },
  { id: 'max_dividend_yield', label: 'Max Dividend Yield', labelKo: '최대 배당수익률', category: 'dividend', type: 'range', unit: '%', minValue: 0, maxValue: 20, step: 0.1 },

  // Technical
  { id: 'beta_min', label: 'Min Beta', labelKo: '최소 베타', category: 'technical', type: 'range', minValue: -2, maxValue: 5, step: 0.1 },
  { id: 'beta_max', label: 'Max Beta', labelKo: '최대 베타', category: 'technical', type: 'range', minValue: -2, maxValue: 5, step: 0.1 },
  { id: 'rsi_min', label: 'Min RSI', labelKo: '최소 RSI', category: 'technical', type: 'range', minValue: 0, maxValue: 100, step: 1 },
  { id: 'rsi_max', label: 'Max RSI', labelKo: '최대 RSI', category: 'technical', type: 'range', minValue: 0, maxValue: 100, step: 1 },

  // Market Movers
  { id: 'trend_strength_min', label: 'Min Trend Strength', labelKo: '최소 추세 강도', category: 'market_movers', type: 'range', minValue: -1, maxValue: 1, step: 0.1, descriptionKo: '장중 추세 강도 (-1 ~ +1)' },
  { id: 'sector_alpha_min', label: 'Min Sector Alpha', labelKo: '최소 섹터 알파', category: 'market_movers', type: 'range', unit: '%', minValue: -50, maxValue: 50, step: 1, descriptionKo: '섹터 ETF 대비 초과수익률' },
  { id: 'volatility_pct_min', label: 'Min Volatility %ile', labelKo: '최소 변동성 백분위', category: 'market_movers', type: 'range', unit: '%ile', minValue: 0, maxValue: 100, step: 1 },

  // Sector (select)
  {
    id: 'sector',
    label: 'Sector',
    labelKo: '섹터',
    category: 'other',
    type: 'select',
    options: [
      { value: 'Technology', label: '기술' },
      { value: 'Healthcare', label: '헬스케어' },
      { value: 'Financial Services', label: '금융' },
      { value: 'Consumer Cyclical', label: '경기소비재' },
      { value: 'Industrials', label: '산업재' },
      { value: 'Energy', label: '에너지' },
      { value: 'Communication Services', label: '통신' },
      { value: 'Real Estate', label: '부동산' },
      { value: 'Utilities', label: '유틸리티' },
      { value: 'Basic Materials', label: '소재' },
      { value: 'Consumer Defensive', label: '필수소비재' },
    ],
    isPopular: true,
  },
];
