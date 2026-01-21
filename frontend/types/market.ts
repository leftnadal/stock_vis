/**
 * Market Movers 타입 정의
 */

// 기존 타입 (stocks API용)
export interface MarketMover {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changes_percentage: number;
  direction: 'up' | 'down';
  formatted_change: string;
  exchange?: string;  // NASDAQ, NYSE 등
}

export interface MarketMoversResponse {
  gainers: MarketMover[];
  losers: MarketMover[];
  actives: MarketMover[];
  cached_at: string | null;
  last_updated: string;
}

// 신규 타입 (serverless API용 - Phase 1 + Phase 2)
export interface MarketMoverItem {
  rank: number;
  symbol: string;
  company_name: string;
  price: string;
  change_percent: string;
  change_amount?: string;
  volume: number;
  // 섹터/산업 정보
  sector?: string | null;
  industry?: string | null;
  open_price?: string;
  high?: string;
  low?: string;
  // Phase 1 지표
  rvol?: string;
  rvol_display: string;
  trend_strength?: string;
  trend_display: string;
  // Phase 2 지표
  sector_alpha?: string;
  sector_alpha_display: string;
  etf_sync_rate?: string;
  etf_sync_display: string;
  volatility_pct?: number;
  volatility_pct_display: string;
  data_quality?: {
    has_20d_volume: boolean;
    has_ohlc: boolean;
  };
}

export interface ServerlessMarketMoversResponse {
  success: boolean;
  data: {
    date: string;
    type: 'gainers' | 'losers' | 'actives';
    count: number;
    movers: MarketMoverItem[];
  };
}

export type MoverType = 'gainers' | 'losers' | 'actives';

export interface MoverTabConfig {
  id: MoverType;
  label: string;
  labelKo: string;
  icon: string;
  color: string;
  description: string;
}

export const MOVER_TABS: MoverTabConfig[] = [
  {
    id: 'gainers',
    label: 'Top Gainers',
    labelKo: '상승',
    icon: 'trending-up',
    color: 'emerald',
    description: '최근 거래일 기준 상승률 상위 종목',
  },
  {
    id: 'losers',
    label: 'Top Losers',
    labelKo: '하락',
    icon: 'trending-down',
    color: 'red',
    description: '최근 거래일 기준 하락률 상위 종목',
  },
  {
    id: 'actives',
    label: 'Most Active',
    labelKo: '거래량',
    icon: 'bar-chart',
    color: 'amber',
    description: '최근 거래일 기준 거래량 상위 종목',
  },
];
