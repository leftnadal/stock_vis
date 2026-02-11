/**
 * ETF Holdings Phase 3 타입 정의
 */

export type ETFTier = 'sector' | 'theme';

export type ETFSyncStatus = 'synced' | 'pending' | 'syncing' | 'failed';

export type ThemeConfidence = 'high' | 'medium-high' | 'medium';

/**
 * ETF 프로필 정보
 */
export interface ETFProfile {
  symbol: string;
  name: string;
  tier: ETFTier;
  theme_id: string;
  is_active: boolean;
  csv_url: string | null;
  last_updated: string | null;
  last_row_count: number;
  holdings_count: number;
  last_error: string | null;
  status: ETFSyncStatus;
}

/**
 * ETF Holdings 정보
 */
export interface ETFHolding {
  rank: number;
  symbol: string;
  weight: number;
  shares: number | null;
  market_value: number | null;
}

/**
 * 테마 정보
 */
export interface Theme {
  id: string;
  name: string;
  icon: string;
  etf_symbol: string | null;
  stock_count: number;
}

/**
 * 테마 매칭 정보
 */
export interface ThemeMatch {
  theme_id: string;
  name: string;
  icon: string;
  confidence: ThemeConfidence;
  source: 'etf_holding' | 'keyword' | 'co_mentioned' | 'multi_etf';
  etf_symbol: string | null;
  evidence: string[];
}

/**
 * ETF 동반 종목
 */
export interface ETFPeer {
  symbol: string;
  etfs_in_common: string[];
  total_weight: number;
  reason: string;
}

/**
 * ETF 수집 상태 응답
 */
export interface ETFCollectionStatusResponse {
  success: boolean;
  data: {
    etfs: ETFProfile[];
    summary: {
      total: number;
      synced: number;
      pending: number;
      sector_count: number;
      theme_count: number;
    };
  };
}

/**
 * ETF 동기화 결과
 */
export interface ETFSyncResult {
  etf: string;
  status: 'success' | 'download_failed' | 'parse_failed' | 'error';
  holdings_count?: number;
  last_updated?: string;
  error?: string;
}

/**
 * ETF 동기화 응답
 */
export interface ETFSyncResponse {
  success: boolean;
  data: {
    results: ETFSyncResult[];
    summary: {
      total: number;
      success: number;
      failed: number;
    };
  };
}

/**
 * ETF Holdings 응답
 */
export interface ETFHoldingsResponse {
  success: boolean;
  data: {
    etf: {
      symbol: string;
      name: string;
      tier: ETFTier;
      theme_id: string;
      last_updated: string | null;
    };
    holdings: ETFHolding[];
    total_count: number;
  };
}

/**
 * 테마 목록 응답
 */
export interface ThemeListResponse {
  success: boolean;
  data: {
    themes: Theme[];
  };
}

/**
 * 종목 테마 응답
 */
export interface StockThemesResponse {
  success: boolean;
  data: {
    symbol: string;
    themes: ThemeMatch[];
  };
}

/**
 * ETF 동반 종목 응답
 */
export interface ETFPeersResponse {
  success: boolean;
  data: {
    symbol: string;
    peers: ETFPeer[];
  };
}
