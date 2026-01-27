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
  per_min?: number;
  per_max?: number;
  roe_min?: number;
  market_cap_min?: number;
  market_cap_max?: number;
  sector?: string;
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
      if (filters.beta_more_than !== undefined) {
        params.append('beta_more_than', filters.beta_more_than.toString());
      }
      if (filters.beta_lower_than !== undefined) {
        params.append('beta_lower_than', filters.beta_lower_than.toString());
      }

      // 거래량 필터
      if (filters.volume_more_than !== undefined) {
        params.append('volume_more_than', filters.volume_more_than.toString());
      }
      if (filters.volume_lower_than !== undefined) {
        params.append('volume_lower_than', filters.volume_lower_than.toString());
      }

      // 배당률 필터
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
    const stocks = result.data?.stocks || result.data || [];

    // PER/ROE 클라이언트 사이드 필터링 (FMP API가 직접 지원하지 않는 경우)
    let filteredStocks = stocks;
    if (filters?.per_min !== undefined || filters?.per_max !== undefined || filters?.roe_min !== undefined) {
      filteredStocks = stocks.filter((stock: ScreenerStock) => {
        const pe = stock.pe_ratio ?? 0;
        const roe = stock.roe ?? 0;

        if (filters.per_min !== undefined && pe < filters.per_min) return false;
        if (filters.per_max !== undefined && pe > filters.per_max) return false;
        if (filters.roe_min !== undefined && roe < filters.roe_min) return false;

        return true;
      });
    }

    return filteredStocks;
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
