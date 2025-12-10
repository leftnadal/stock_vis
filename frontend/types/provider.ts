// types/provider.ts
/**
 * Stock Data Provider Types
 *
 * Backend Provider 응답과 호환되는 TypeScript 타입 정의
 */

/**
 * Provider 타입
 */
export type ProviderType = 'alpha_vantage' | 'fmp';

/**
 * 엔드포인트 타입
 */
export type EndpointType =
  | 'quote'
  | 'profile'
  | 'daily_prices'
  | 'weekly_prices'
  | 'balance_sheet'
  | 'income_statement'
  | 'cash_flow'
  | 'search'
  | 'sector';

/**
 * Provider 응답 기본 구조
 */
export interface ProviderResponse<T = unknown> {
  success: boolean;
  data: T | null;
  error: string | null;
  error_code: string | null;
  provider: ProviderType;
  cached: boolean;
  timestamp: string;
  meta: Record<string, unknown>;
}

/**
 * 정규화된 시세 데이터
 */
export interface NormalizedQuote {
  symbol: string;
  price: string;
  open: string | null;
  high: string | null;
  low: string | null;
  volume: number | null;
  previous_close: string | null;
  change: string | null;
  change_percent: string | null;
  latest_trading_day: string | null;
  timestamp: string;
}

/**
 * 정규화된 회사 프로필
 */
export interface NormalizedCompanyProfile {
  symbol: string;
  name: string;
  description: string | null;
  exchange: string | null;
  currency: string | null;
  country: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: string | null;
  pe_ratio: string | null;
  beta: string | null;
  dividend_yield: string | null;
  eps: string | null;
  high_52week: string | null;
  low_52week: string | null;
  moving_avg_50: string | null;
  moving_avg_200: string | null;
  shares_outstanding: number | null;
  website: string | null;
  ceo: string | null;
  full_time_employees: number | null;
  ipo_date: string | null;
}

/**
 * 정규화된 가격 데이터
 */
export interface NormalizedPriceData {
  date: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
  adjusted_close: string | null;
  dividend_amount: string | null;
  split_coefficient: string | null;
}

/**
 * 정규화된 검색 결과
 */
export interface NormalizedSearchResult {
  symbol: string;
  name: string;
  type: string | null;
  exchange: string | null;
  currency: string | null;
  match_score: number | null;
}

/**
 * Rate Limit 상태
 */
export interface RateLimitStatus {
  current: number;
  limit: number;
  remaining: number;
  reset_in: number;
}

/**
 * Provider Rate Limit 상태
 */
export interface ProviderRateLimitStatus {
  provider: ProviderType;
  request_delay: number;
  limits: {
    per_minute?: RateLimitStatus;
    per_day?: RateLimitStatus;
  };
}

/**
 * Provider 상태
 */
export interface ProviderStatus {
  provider: ProviderType;
  available: boolean;
  rate_limit: {
    provider: string;
    calls_per_minute: number;
    daily_limit: number;
    request_delay: number;
  };
}

/**
 * 캐시 통계
 */
export interface CacheStats {
  hits: number;
  misses: number;
  total: number;
  hit_rate_percent: number;
  since: string;
}

/**
 * Admin Provider 상태 응답
 */
export interface AdminProviderStatusResponse {
  providers: Record<EndpointType, ProviderStatus | { error: string }>;
  feature_flags: Record<EndpointType, ProviderType>;
  fallback_enabled: boolean;
}

/**
 * Admin Provider 설정 응답
 */
export interface AdminProviderConfigResponse {
  feature_flags: Record<EndpointType, ProviderType>;
  cache_ttl: Record<EndpointType, number>;
  rate_limits: Record<
    ProviderType,
    {
      per_minute: number;
      per_day: number;
      request_delay: number;
    }
  >;
  fallback_enabled: boolean;
}

/**
 * Provider 테스트 응답
 */
export interface ProviderTestResponse {
  provider: ProviderType;
  symbol: string;
  success: boolean;
  cached: boolean;
  data: {
    price: string | null;
    change: string | null;
  } | null;
  error: string | null;
}

/**
 * API 사용량 정보 (UI 표시용)
 */
export interface ApiUsageInfo {
  provider: ProviderType;
  daily_calls: number;
  daily_limit: number;
  remaining: number;
  usage_percent: number;
  last_request: string | null;
}
