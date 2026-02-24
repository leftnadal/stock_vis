// ========================================
// Admin Dashboard Types
// ========================================

export type AdminTab = 'overview' | 'stocks' | 'screener' | 'market-pulse' | 'news' | 'system';

// ========================================
// Overview
// ========================================

export interface AdminOverviewResponse {
  summary: {
    stocks: {
      total: number;
      sp500_active: number;
      with_todays_price: number;
      coverage_pct: number;
    };
    tasks_24h: {
      total: number;
      success: number;
      failure: number;
      success_rate: number;
    };
    data_freshness: {
      last_trading_day: string;
      is_today_trading_day: boolean;
      movers: boolean;
      keywords: boolean;
      breadth: boolean;
      news_keywords: boolean;
    };
    news: {
      articles_24h: number;
    };
  };
  issues: AdminIssue[];
}

export interface AdminIssue {
  severity: 'error' | 'warning' | 'info';
  category: string;
  title: string;
  detail: string;
  symbols?: string[];
  suggested_action?: string | null;
}

// ========================================
// Stocks
// ========================================

export interface AdminStocksStatus {
  last_trading_day: string;
  sp500: {
    active_count: number;
    latest_update: string | null;
  };
  daily_price: {
    latest_date: string | null;
    is_fresh: boolean;
    total_records: number;
    distinct_stocks: number;
    coverage: number;
    missing_count: number;
    missing_symbols: string[];
  };
  weekly_price: {
    latest_date: string | null;
    is_fresh: boolean;
    total_records: number;
  };
  balance_sheet: DataSourceStatus;
  income_statement: DataSourceStatus;
  cash_flow: DataSourceStatus;
}

interface DataSourceStatus {
  latest_date: string | null;
  is_fresh: boolean;
  total_records: number;
  distinct_stocks: number;
}

// ========================================
// Screener
// ========================================

export interface AdminScreenerStatus {
  breadth: {
    today: {
      date: string;
      signal: string | null;
      advance_decline_ratio: string | null;
      exists: boolean;
    };
    history: BreadthHistoryItem[];
  };
  sector_performance: {
    count: number;
    expected: number;
    complete: boolean;
  };
  alerts: {
    active_count: number;
    recent_history: AlertHistoryItem[];
  };
}

interface BreadthHistoryItem {
  date: string;
  breadth_signal: string;
  advance_decline_ratio: string;
  advancing_count: number;
  declining_count: number;
}

interface AlertHistoryItem {
  id: number;
  alert__name: string;
  triggered_at: string;
  matched_count: number;
  status: string;
  read_at: string | null;
}

// ========================================
// Market Pulse
// ========================================

export interface AdminMarketPulseStatus {
  movers: {
    date: string;
    by_type: Record<string, number>;
    total: number;
  };
  keywords: {
    date: string;
    by_status: Record<string, number>;
  };
  cache: {
    fear_greed: boolean;
    market_pulse: boolean;
  };
  economic_indicators: {
    total: number;
  };
}

// ========================================
// News
// ========================================

export interface AdminNewsStatus {
  articles: {
    total: number;
    last_24h: number;
    last_7d: number;
  };
  source_distribution: Array<{
    source: string;
    count: number;
  }>;
  keyword_history: Array<{
    date: string;
    status: string;
    total_news_count: number;
  }>;
  sentiment: {
    avg_7d: string | null;
    coverage_symbols: number;
  };
  categories?: {
    active: number;
    total: number;
    by_priority: { high: number; medium: number; low: number };
    latest_collection: {
      name: string;
      collected_at: string;
      article_count: number;
    } | null;
  };
}

// ========================================
// News Collection Categories
// ========================================

export type NewsCategoryType = 'sector' | 'sub_sector' | 'custom';
export type NewsCategoryPriority = 'high' | 'medium' | 'low';

export interface NewsCollectionCategory {
  id: number;
  name: string;
  category_type: NewsCategoryType;
  value: string;
  is_active: boolean;
  priority: NewsCategoryPriority;
  max_symbols: number;
  resolved_symbol_count: number;
  resolved_symbols_preview: string[];
  last_collected_at: string | null;
  last_article_count: number;
  last_symbol_count: number;
  total_collections: number;
  last_error: string;
  created_at: string;
  updated_at: string;
}

export interface NewsCategoryCreateRequest {
  name: string;
  category_type: NewsCategoryType;
  value: string;
  is_active?: boolean;
  priority?: NewsCategoryPriority;
  max_symbols?: number;
}

export interface NewsCategoryUpdateRequest {
  name?: string;
  category_type?: NewsCategoryType;
  value?: string;
  is_active?: boolean;
  priority?: NewsCategoryPriority;
  max_symbols?: number;
}

export interface SectorOption {
  value: string;
  count: number;
}

export interface SubSectorOption {
  value: string;
  sector: string;
  count: number;
}

export interface SectorOptionsResponse {
  sectors: SectorOption[];
  sub_sectors: SubSectorOption[];
}

// ========================================
// System
// ========================================

export interface LatestTaskRun {
  task_name: string;
  status: string;
  date_done: string | null;
  result: string;
}

export interface AdminSystemStatus {
  task_summary: Array<{
    task_name: string;
    status: string;
    count: number;
  }>;
  latest_task_runs: LatestTaskRun[];
  recent_failures: Array<{
    task_name: string;
    date_done: string | null;
    worker: string;
    traceback: string;
  }>;
  rate_limits: Record<string, unknown>;
  cache_stats: Record<string, unknown>;
  db_table_sizes: Array<{
    table: string;
    row_count: number;
  }>;
}

export interface TaskLogEntry {
  id: string;
  task_id: string;
  task_name: string;
  status: string;
  date_done: string | null;
  worker: string;
  traceback: string;
  result: string;
}

export interface TaskLogParams {
  task_name?: string;
  status?: string;
  hours?: number;
  limit?: number;
}

// ========================================
// Health Check (기존 엔드포인트 재사용)
// ========================================

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  components: Record<string, {
    status: string;
    type?: string;
    active?: string;
    error?: string;
  }>;
}

// ========================================
// Admin Actions
// ========================================

export interface AdminActionMeta {
  label: string;
  dangerous: boolean;
  cooldown_seconds: number;
  cooldown_remaining: number;
  params: string[];
  required_params: string[];
  cost_estimate?: string;
}

export interface AdminActionsResponse {
  actions: Record<string, AdminActionMeta>;
}

export interface AdminActionRequest {
  action: string;
  params?: Record<string, string | number | boolean>;
  confirm?: boolean;
}

export interface AdminActionResponse {
  success: boolean;
  data?: { task_id: string; action: string; label: string; message: string };
  error?: string;
  requires_confirm?: boolean;
  label?: string;
  cost_estimate?: string;
  cooldown_remaining?: number;
}

export interface AdminTaskStatus {
  task_id: string;
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'UNKNOWN';
  result: string | null;
  date_done: string | null;
  traceback: string | null;
}

export interface ProviderStatusResponse {
  providers: Record<string, {
    provider?: string;
    available?: boolean;
    rate_limit?: unknown;
    error?: string;
  }>;
  feature_flags: Record<string, string>;
  fallback_enabled: boolean;
}
