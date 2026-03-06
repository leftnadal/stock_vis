// Stock service for fetching stock data

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface StockQuote {
  symbol: string;
  stock_name: string;
  real_time_price: number;
  high_price: number;
  low_price: number;
  open_price: number;
  previous_close: number;
  volume: number;
  change: number;
  change_percent: string;
  market_capitalization?: number;
  pe_ratio?: number;
  dividend_yield?: number;
  week_52_high?: number;
  week_52_low?: number;
  last_updated?: string;
}

export interface ChartData {
  date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
}

export interface StockOverview {
  symbol: string;
  stock_name: string;
  description?: string;
  sector?: string;
  industry?: string;
  country?: string;
  exchange?: string;
  currency?: string;
  market_capitalization?: number;
  ebitda?: number;
  pe_ratio?: number;
  peg_ratio?: number;
  book_value?: number;
  dividend_per_share?: number;
  dividend_yield?: number;
  eps?: number;
  revenue_per_share_ttm?: number;
  profit_margin?: number;
  operating_margin_ttm?: number;
  return_on_assets_ttm?: number;
  return_on_equity_ttm?: number;
  revenue_ttm?: number;
  gross_profit_ttm?: number;
  diluted_eps_ttm?: number;
  quarterly_earnings_growth_yoy?: number;
  quarterly_revenue_growth_yoy?: number;
  analyst_target_price?: number;
  trailing_pe?: number;
  forward_pe?: number;
  price_to_sales_ratio_ttm?: number;
  price_to_book_ratio?: number;
  ev_to_revenue?: number;
  ev_to_ebitda?: number;
  beta?: number;
  week_52_high?: number;
  week_52_low?: number;
  day_50_moving_average?: number;
  day_200_moving_average?: number;
  shares_outstanding?: number;
  dividend_date?: string;
  ex_dividend_date?: string;
  // 한글 개요 (LLM 생성)
  korean_overview?: {
    summary: string;
    business_model: string;
    competitive_edge: string;
    risk_factors: string;
    generated_at: string;
    llm_model: string;
  } | null;
}

// Meta information for data freshness tracking
export interface DataMeta {
  source: 'db' | 'fmp' | 'fmp_realtime' | 'alpha_vantage' | 'yfinance' | 'unknown';
  synced_at: string | null;
  freshness: 'fresh' | 'stale' | 'expired';
  can_sync: boolean;
}

export interface SyncResponse {
  symbol: string;
  status: 'success' | 'partial' | 'failed';
  synced: Record<string, { success: boolean; source?: string; error?: string }>;
  next_sync_available: string;
}

export interface OverviewWithMeta {
  overview: StockOverview;
  _meta: DataMeta | null;
}

export interface FinancialStatement {
  fiscal_date_ending: string;
  fiscal_year: number;
  fiscal_quarter?: number;
  period_type: 'annual' | 'quarterly';
  [key: string]: any; // Other financial metrics
}

export const stockService = {
  // Get stock quote (basic info) - using overview API which contains quote data
  async getStockQuote(symbol: string): Promise<StockQuote> {
    const response = await fetch(`${API_URL}/stocks/api/overview/${symbol}/`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch stock quote');
    }

    const result = await response.json();

    // Extract quote data from overview response
    const data = result.data;
    return {
      symbol: data.symbol,
      stock_name: data.stock_name,
      real_time_price: parseFloat(data.real_time_price) || 0,
      high_price: parseFloat(data.high_price) || parseFloat(data.real_time_price) || 0,
      low_price: parseFloat(data.low_price) || parseFloat(data.real_time_price) || 0,
      open_price: parseFloat(data.open_price) || parseFloat(data.real_time_price) || 0,
      previous_close: parseFloat(data.previous_close) || 0,
      volume: data.volume || 0,
      change: parseFloat(data.change) || 0,
      change_percent: data.change_percent || '0%',
      market_capitalization: parseFloat(data.market_capitalization) || 0,
      pe_ratio: parseFloat(data.pe_ratio) || 0,
      dividend_yield: parseFloat(data.dividend_yield) || 0,
      week_52_high: parseFloat(data.week_52_high) || 0,
      week_52_low: parseFloat(data.week_52_low) || 0,
      last_updated: data.last_updated,
    };
  },

  // Get stock overview (detailed info)
  async getStockOverview(symbol: string): Promise<StockOverview> {
    const result = await this.getStockOverviewWithMeta(symbol);
    return result.overview;
  },

  // Get stock overview with meta information
  async getStockOverviewWithMeta(symbol: string): Promise<OverviewWithMeta> {
    const response = await fetch(`${API_URL}/stocks/api/overview/${symbol}/`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error('Failed to fetch stock overview') as any;
      error.response = { data: errorData, status: response.status };
      throw error;
    }

    const result = await response.json();
    const data = result.data;

    // Transform the data to match our interface
    const overview: StockOverview = {
      symbol: data.symbol,
      stock_name: data.stock_name,
      description: data.description,
      sector: data.sector,
      industry: data.industry,
      country: data.country,
      exchange: data.exchange,
      currency: data.currency,
      market_capitalization: parseFloat(data.market_capitalization) || undefined,
      ebitda: parseFloat(data.ebitda) || undefined,
      pe_ratio: parseFloat(data.pe_ratio) || undefined,
      peg_ratio: parseFloat(data.peg_ratio) || undefined,
      book_value: parseFloat(data.book_value) || undefined,
      dividend_per_share: parseFloat(data.dividend_per_share) || undefined,
      dividend_yield: parseFloat(data.dividend_yield) || undefined,
      eps: parseFloat(data.eps) || undefined,
      revenue_per_share_ttm: parseFloat(data.revenue_per_share_ttm) || undefined,
      profit_margin: parseFloat(data.profit_margin) || undefined,
      operating_margin_ttm: parseFloat(data.operating_margin_ttm) || undefined,
      return_on_assets_ttm: parseFloat(data.return_on_assets_ttm) || undefined,
      return_on_equity_ttm: parseFloat(data.return_on_equity_ttm) || undefined,
      revenue_ttm: parseFloat(data.revenue_ttm) || undefined,
      gross_profit_ttm: parseFloat(data.gross_profit_ttm) || undefined,
      diluted_eps_ttm: parseFloat(data.diluted_eps_ttm) || undefined,
      quarterly_earnings_growth_yoy: parseFloat(data.quarterly_earnings_growth_yoy) || undefined,
      quarterly_revenue_growth_yoy: parseFloat(data.quarterly_revenue_growth_yoy) || undefined,
      analyst_target_price: parseFloat(data.analyst_target_price) || undefined,
      trailing_pe: parseFloat(data.trailing_pe) || undefined,
      forward_pe: parseFloat(data.forward_pe) || undefined,
      price_to_sales_ratio_ttm: parseFloat(data.price_to_sales_ratio_ttm) || undefined,
      price_to_book_ratio: parseFloat(data.price_to_book_ratio) || undefined,
      ev_to_revenue: parseFloat(data.ev_to_revenue) || undefined,
      ev_to_ebitda: parseFloat(data.ev_to_ebitda) || undefined,
      beta: parseFloat(data.beta) || undefined,
      week_52_high: parseFloat(data.week_52_high) || undefined,
      week_52_low: parseFloat(data.week_52_low) || undefined,
      day_50_moving_average: parseFloat(data.day_50_moving_average) || undefined,
      day_200_moving_average: parseFloat(data.day_200_moving_average) || undefined,
      shares_outstanding: parseFloat(data.shares_outstanding) || undefined,
      dividend_date: data.dividend_date,
      ex_dividend_date: data.ex_dividend_date,
      korean_overview: data.korean_overview || null,
    };

    // Extract meta information
    const _meta: DataMeta | null = result._meta || null;

    return { overview, _meta };
  },

  // Sync stock data from external API to DB
  async syncData(
    symbol: string,
    dataTypes: string[] = ['overview'],
    force: boolean = false
  ): Promise<SyncResponse> {
    // 인증 토큰 가져오기 (선택적)
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}/stocks/api/sync/${symbol}/`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ data_types: dataTypes, force }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error('Failed to sync stock data') as any;
      error.response = { data: errorData, status: response.status };
      throw error;
    }

    return response.json();
  },

  // Get sync status
  async getSyncStatus(symbol: string): Promise<any> {
    const response = await fetch(`${API_URL}/stocks/api/sync/${symbol}/`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to get sync status');
    }

    return response.json();
  },

  // Get chart data
  async getChartData(
    symbol: string,
    type: 'daily' | 'weekly' = 'daily',
    period: string = '1m'
  ): Promise<{ data: ChartData[]; [key: string]: any }> {
    // days 파라미터 처리
    const params = new URLSearchParams({ type });

    if (period.startsWith('days=')) {
      // days 파라미터인 경우
      params.append('days', period.split('=')[1]);
    } else {
      // period 파라미터인 경우
      params.append('period', period);
    }

    const url = `${API_URL}/stocks/api/chart/${symbol}/?${params}`;
    console.log('Fetching chart data from:', url);

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Chart data fetch failed:', response.status, errorText);
      throw new Error(`Failed to fetch chart data: ${response.status} - ${errorText}`);
    }

    return response.json();
  },

  // Get balance sheet
  async getBalanceSheet(
    symbol: string,
    period: 'annual' | 'quarterly' = 'annual',
    limit: number = 5
  ): Promise<FinancialStatement[]> {
    const params = new URLSearchParams({
      period,
      limit: limit.toString(),
    });

    const url = `${API_URL}/stocks/api/balance-sheet/${symbol}/?${params}`;
    console.log('[DEBUG] Balance Sheet URL:', url);

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    console.log('[DEBUG] Balance Sheet Response:', response.status, response.statusText);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[DEBUG] Balance Sheet Error Body:', errorText);
      throw new Error('Failed to fetch balance sheet');
    }

    const data = await response.json();
    return data.data || [];
  },

  // Get income statement
  async getIncomeStatement(
    symbol: string,
    period: 'annual' | 'quarterly' = 'annual',
    limit: number = 5
  ): Promise<FinancialStatement[]> {
    const params = new URLSearchParams({
      period,
      limit: limit.toString(),
    });

    const response = await fetch(`${API_URL}/stocks/api/income-statement/${symbol}/?${params}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch income statement');
    }

    const data = await response.json();
    return data.data || [];
  },

  // Get cash flow statement
  async getCashFlow(
    symbol: string,
    period: 'annual' | 'quarterly' = 'annual',
    limit: number = 5
  ): Promise<FinancialStatement[]> {
    const params = new URLSearchParams({
      period,
      limit: limit.toString(),
    });

    const url = `${API_URL}/stocks/api/cashflow/${symbol}/?${params}`;
    console.log('[DEBUG] Cash Flow URL:', url);

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    console.log('[DEBUG] Cash Flow Response:', response.status, response.statusText);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[DEBUG] Cash Flow Error Body:', errorText);
      throw new Error('Failed to fetch cash flow');
    }

    const data = await response.json();
    return data.data || [];
  },

  // Search for stocks (will be integrated later)
  async searchStocks(query: string): Promise<any[]> {
    const response = await fetch(`${API_URL}/stocks/api/search/?q=${encodeURIComponent(query)}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to search stocks');
    }

    const data = await response.json();
    return data.results || [];
  },

  // Get key metrics (fundamental data)
  async getKeyMetrics(
    symbol: string,
    period: 'annual' | 'quarterly' = 'annual',
    limit: number = 5
  ): Promise<any[]> {
    const params = new URLSearchParams({
      period,
      limit: limit.toString(),
    });

    const response = await fetch(`${API_URL}/stocks/api/key-metrics/${symbol}/?${params}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch key metrics');
    }

    const data = await response.json();
    return data.data || [];
  },

  // Get financial ratios
  async getFinancialRatios(
    symbol: string,
    period: 'annual' | 'quarterly' = 'annual',
    limit: number = 5
  ): Promise<any[]> {
    const params = new URLSearchParams({
      period,
      limit: limit.toString(),
    });

    const response = await fetch(`${API_URL}/stocks/api/ratios/${symbol}/?${params}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch financial ratios');
    }

    const data = await response.json();
    return data.data || [];
  },

  // Get DCF valuation
  async getDCF(symbol: string): Promise<any> {
    const response = await fetch(`${API_URL}/stocks/api/dcf/${symbol}/`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch DCF valuation');
    }

    const data = await response.json();
    return data.data || null;
  },

  // Get investment rating
  async getRating(symbol: string): Promise<any> {
    const response = await fetch(`${API_URL}/stocks/api/rating/${symbol}/`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch investment rating');
    }

    const data = await response.json();
    return data.data || null;
  },

  // Get all fundamentals at once
  async getAllFundamentals(symbol: string): Promise<any> {
    const [keyMetrics, ratios, dcf, rating] = await Promise.allSettled([
      this.getKeyMetrics(symbol, 'annual', 5),
      this.getFinancialRatios(symbol, 'annual', 5),
      this.getDCF(symbol),
      this.getRating(symbol),
    ]);

    return {
      symbol,
      keyMetrics: keyMetrics.status === 'fulfilled' ? keyMetrics.value : [],
      ratios: ratios.status === 'fulfilled' ? ratios.value : [],
      dcf: dcf.status === 'fulfilled' ? dcf.value : null,
      rating: rating.status === 'fulfilled' ? rating.value : null,
    };
  },
};