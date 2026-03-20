// ============================================================
// Pipeline Health
// ============================================================

export type PhaseStatus = 'ok' | 'warning' | 'error' | 'stale';

export interface PipelinePhase {
  phase: number;
  name: string;
  expected_interval_hours: number;
  weekday_only: boolean;
  last_run: string | null;
  hours_since_last_run: number | null;
  status: PhaseStatus;
  // Phase 1 추가 필드
  recent_errors?: number;
  recent_new?: number;
  providers_active?: string[];
  // Phase 2 추가 필드
  classified_today?: number;
  errors_today?: number;
  // Phase 3 추가 필드
  analyzed_today?: number;
  pending?: number;
  // Phase 4 추가 필드
  last_label_run?: string | null;
  last_neo4j_run?: string | null;
  labeled_total?: number;
  neo4j_available?: boolean;
  // Phase 5 추가 필드
  deployed_version?: string;
  deployed_f1?: number;
  deployment_status?: string;
  // Phase 6 추가 필드
  lightgbm_ready?: boolean;
  lightgbm_conditions?: {
    data_sufficient: boolean;
    lr_stagnation: boolean;
    feature_stability: boolean;
  };
  [key: string]: unknown;
}

export interface MLSummary {
  deployed_version: string;
  deployed_f1: number;
  deployment_status: string;
  labeled_data_count: number;
  ready_for_training: boolean;
}

export interface LLMSummary {
  total_analyzed_today: number;
  prompt_tokens_today: number;
  completion_tokens_today: number;
  error_rate_today: number;
}

export interface PipelineHealthResponse {
  generated_at: string;
  is_weekend_kst: boolean;
  phases: PipelinePhase[];
  ml_summary: MLSummary;
  llm_summary: LLMSummary;
}

// ============================================================
// Collection Logs
// ============================================================

export interface CollectionLogEntry {
  id: number;
  task_name: string;
  provider: string;
  executed_at: string;
  symbols_tried: number;
  articles_new: number;
  articles_dup: number;
  api_calls: number;
  errors: number;
  duration_sec: number;
}

export interface ProviderStats {
  total_runs: number;
  total_new: number;
  total_dup: number;
  total_errors: number;
  avg_duration_sec: number;
  success_rate: number;
}

export interface DailySummary {
  date: string;
  total_new: number;
  total_dup: number;
  total_errors: number;
  runs: number;
}

export interface CollectionLogsResponse {
  period_days: number;
  total_records: number;
  logs: CollectionLogEntry[];
  aggregated: {
    by_provider: Record<string, ProviderStats>;
    daily_summary: DailySummary[];
  };
}

// ============================================================
// ML Trend
// ============================================================

export interface MLModelEntry {
  model_version: string;
  trained_at: string;
  algorithm: string;
  f1_score: number;
  precision: number;
  recall: number;
  accuracy: number;
  training_samples: number;
  safety_gate_passed: boolean;
  deployment_status: 'deployed' | 'shadow' | 'rolled_back' | 'archived';
}

export interface MLTrendResponse {
  weeks: number;
  history: MLModelEntry[];
  latest_feature_importance: Record<string, number>;
  trend_summary: {
    f1_direction: 'improving' | 'declining' | 'stable';
    f1_change_total: number;
    avg_f1: number;
    consecutive_decline: boolean;
  };
}

// ============================================================
// LLM Usage
// ============================================================

export interface LLMUsageDailyEntry {
  date: string;
  status: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  generation_time_ms: number;
  total_news_analyzed: number;
}

export interface LLMUsageResponse {
  period_days: number;
  keyword_extraction: {
    daily: LLMUsageDailyEntry[];
    totals: {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
      success_days: number;
      failed_days: number;
      avg_generation_time_ms: number;
    };
  };
  deep_analysis: {
    total_analyzed: number;
    today_analyzed: number;
    pending_today: number;
    tier_breakdown: {
      A: number;
      B: number;
      C: number;
    };
    coverage_warning: string;
  };
}
