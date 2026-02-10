// Strategy Analysis service for fetching market data and stock screener

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface MajorIndex {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: string;
  sparkline?: number[];
}

export interface ScreenerStock {
  symbol: string;
  name?: string;
  company_name?: string;
  price?: number;
  change?: number;
  change_percent?: string;
  changes_percentage?: number;
  previous_close?: number;
  day_high?: number;
  day_low?: number;
  open_price?: number;
  market_cap?: number;
  formatted_market_cap?: string;
  pe_ratio?: number;
  pe?: number;
  eps?: number;
  roe?: number;
  sector?: string;
  industry?: string;
  exchange?: string;
  exchange_short_name?: string;
  country?: string;
  volume?: number;
  formatted_volume?: string;
  beta?: number;
  dividend_yield?: number;
  last_annual_dividend?: number;
  is_etf?: boolean;
  is_fund?: boolean;
  is_actively_trading?: boolean;
}

export interface ScreenerFilters {
  // URL 파라미터 (프론트엔드 UI)
  per_min?: number;
  per_max?: number;
  roe_min?: number;
  roe_max?: number;
  market_cap_min?: number;
  market_cap_max?: number;
  sector?: string;
  sectors?: string[];
  beta_min?: number;
  beta_max?: number;
  dividend_min?: number;
  volume_min?: number;

  // === Enhanced 필터 (Phase 3: PE/ROE/EPS Growth 등) ===
  eps_growth_min?: number;
  eps_growth_max?: number;
  revenue_growth_min?: number;
  revenue_growth_max?: number;
  debt_equity_max?: number;
  current_ratio_min?: number;
  rsi_min?: number;
  rsi_max?: number;
  change_percent_min?: number;
  change_percent_max?: number;

  // 프리셋 필터 호환 (백엔드 스타일)
  min_pe?: number;
  max_pe?: number;
  min_roe?: number;
  min_market_cap?: number;
  max_market_cap?: number;
  min_dividend_yield?: number;
  min_volume?: number;

  // 백엔드 API 파라미터
  market_cap_more_than?: number;
  market_cap_lower_than?: number;
  price_more_than?: number;
  price_lower_than?: number;
  beta_more_than?: number;
  beta_lower_than?: number;
  volume_more_than?: number;
  volume_lower_than?: number;
  dividend_more_than?: number;
  dividend_lower_than?: number;
  is_etf?: boolean;
  is_actively_trading?: boolean;
  exchange?: string;
  limit?: number;
}

export const strategyService = {
  // Get major indices (S&P 500, NASDAQ, Dow Jones)
  async getMajorIndices(): Promise<MajorIndex[]> {
    const response = await fetch(`${API_URL}/stocks/api/quotes/major-indices/`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch major indices');
    }

    const result = await response.json();
    return result.data || [];
  },

  // Get screener results
  async getScreenerResults(filters?: ScreenerFilters): Promise<ScreenerStock[]> {
    const params = new URLSearchParams();

    if (filters) {
      // 시가총액 필터 (프론트엔드 호환 + 백엔드 API 파라미터)
      if (filters.market_cap_min !== undefined) {
        params.append('market_cap_more_than', filters.market_cap_min.toString());
      }
      if (filters.market_cap_more_than !== undefined) {
        params.append('market_cap_more_than', filters.market_cap_more_than.toString());
      }
      if (filters.market_cap_max !== undefined) {
        params.append('market_cap_lower_than', filters.market_cap_max.toString());
      }
      if (filters.market_cap_lower_than !== undefined) {
        params.append('market_cap_lower_than', filters.market_cap_lower_than.toString());
      }

      // 가격 필터
      if (filters.price_more_than !== undefined) {
        params.append('price_more_than', filters.price_more_than.toString());
      }
      if (filters.price_lower_than !== undefined) {
        params.append('price_lower_than', filters.price_lower_than.toString());
      }

      // 베타 필터
      if (filters.beta_min !== undefined) {
        params.append('beta_more_than', filters.beta_min.toString());
      }
      if (filters.beta_more_than !== undefined) {
        params.append('beta_more_than', filters.beta_more_than.toString());
      }
      if (filters.beta_max !== undefined) {
        params.append('beta_lower_than', filters.beta_max.toString());
      }
      if (filters.beta_lower_than !== undefined) {
        params.append('beta_lower_than', filters.beta_lower_than.toString());
      }

      // 거래량 필터
      if (filters.volume_min !== undefined) {
        params.append('volume_more_than', filters.volume_min.toString());
      }
      if (filters.volume_more_than !== undefined) {
        params.append('volume_more_than', filters.volume_more_than.toString());
      }
      if (filters.volume_lower_than !== undefined) {
        params.append('volume_lower_than', filters.volume_lower_than.toString());
      }

      // 배당률 필터
      if (filters.dividend_min !== undefined) {
        params.append('dividend_more_than', filters.dividend_min.toString());
      }
      if (filters.dividend_more_than !== undefined) {
        params.append('dividend_more_than', filters.dividend_more_than.toString());
      }
      if (filters.dividend_lower_than !== undefined) {
        params.append('dividend_lower_than', filters.dividend_lower_than.toString());
      }

      // 기타 필터
      if (filters.is_etf !== undefined) {
        params.append('is_etf', filters.is_etf.toString());
      }
      if (filters.is_actively_trading !== undefined) {
        params.append('is_actively_trading', filters.is_actively_trading.toString());
      }
      if (filters.sector) {
        params.append('sector', filters.sector);
      }
      if (filters.exchange) {
        params.append('exchange', filters.exchange);
      }
      if (filters.limit !== undefined) {
        params.append('limit', filters.limit.toString());
      }

      // === Enhanced 필터 (PE/ROE/EPS Growth 등 - 백엔드 EnhancedScreenerService에서 처리) ===
      // PER 필터
      if (filters.per_min !== undefined) {
        params.append('pe_ratio_min', filters.per_min.toString());
      }
      if (filters.min_pe !== undefined) {
        params.append('pe_ratio_min', filters.min_pe.toString());
      }
      if (filters.per_max !== undefined) {
        params.append('pe_ratio_max', filters.per_max.toString());
      }
      if (filters.max_pe !== undefined) {
        params.append('pe_ratio_max', filters.max_pe.toString());
      }

      // ROE 필터
      if (filters.roe_min !== undefined) {
        params.append('roe_min', filters.roe_min.toString());
      }
      if (filters.min_roe !== undefined) {
        params.append('roe_min', filters.min_roe.toString());
      }
      if (filters.roe_max !== undefined) {
        params.append('roe_max', filters.roe_max.toString());
      }

      // EPS Growth 필터
      if (filters.eps_growth_min !== undefined) {
        params.append('eps_growth_min', filters.eps_growth_min.toString());
      }
      if (filters.eps_growth_max !== undefined) {
        params.append('eps_growth_max', filters.eps_growth_max.toString());
      }

      // Revenue Growth 필터
      if (filters.revenue_growth_min !== undefined) {
        params.append('revenue_growth_min', filters.revenue_growth_min.toString());
      }
      if (filters.revenue_growth_max !== undefined) {
        params.append('revenue_growth_max', filters.revenue_growth_max.toString());
      }

      // 재무 건전성 필터
      if (filters.debt_equity_max !== undefined) {
        params.append('debt_equity_max', filters.debt_equity_max.toString());
      }
      if (filters.current_ratio_min !== undefined) {
        params.append('current_ratio_min', filters.current_ratio_min.toString());
      }

      // 기술적 지표 필터 (RSI)
      if (filters.rsi_min !== undefined) {
        params.append('rsi_min', filters.rsi_min.toString());
      }
      if (filters.rsi_max !== undefined) {
        params.append('rsi_max', filters.rsi_max.toString());
      }

      // 변동률 필터
      if (filters.change_percent_min !== undefined) {
        params.append('change_percent_min', filters.change_percent_min.toString());
      }
      if (filters.change_percent_max !== undefined) {
        params.append('change_percent_max', filters.change_percent_max.toString());
      }
    }

    const url = `${API_URL}/stocks/api/screener/${params.toString() ? `?${params}` : ''}`;

    // 인증 토큰 가져오기
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch screener results: ${response.status}`);
    }

    const result = await response.json();

    // 응답 데이터 변환 (백엔드 응답 형식에 맞춤)
    // Enhanced 필터 (PE/ROE/EPS Growth 등)는 백엔드 EnhancedScreenerService에서 처리됨
    const stocks = result.data?.stocks || result.data || [];

    return stocks;
  },

  // Get large cap stocks
  async getLargeCapStocks(): Promise<ScreenerStock[]> {
    const response = await fetch(`${API_URL}/stocks/api/screener/large-cap/`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch large cap stocks');
    }

    const result = await response.json();
    return result.data || [];
  },
};
