// 주식 관련 타입 정의

export interface Stock {
  symbol: string;
  stock_name: string;
  description?: string;
  sector: string;
  industry?: string;
  exchange?: string;
  currency?: string;
  real_time_price: string;
  change: string;
  change_percent?: string | null;
  change_percent_numeric?: number;
  previous_close: string;
  volume: number;
  market_capitalization: string;
  market_cap_formatted?: string;
}

export interface StockListItem {
  symbol: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  changePercent: number | null;
  marketCap: number;
}

export interface ChartDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartResponse {
  symbol: string;
  period: string;
  chart_type: string;
  data: ChartDataPoint[];
  count: number;
  start_date: string;
  end_date: string;
  available_periods: string[];
}

export interface StockOverview {
  symbol: string;
  tab: string;
  data: {
    symbol: string;
    stock_name: string;
    description: string;
    sector: string;
    industry: string;
    exchange: string;
    currency: string;
    official_site?: string;
    real_time_price: string;
    change: string;
    change_percent?: string | null;
    change_percent_numeric: number;
    previous_close: string;
    week_52_high?: string | null;
    week_52_low?: string | null;
    volume: number;
    volume_formatted?: string | null;
    market_capitalization: string;
    market_cap_formatted: string;
    shares_outstanding?: string | null;
    ebitda?: string | null;
    pe_ratio?: string | null;
    peg_ratio?: string | null;
    book_value?: string | null;
    eps?: string | null;
    dividend_per_share?: string | null;
    dividend_yield?: string | null;
    dividend_date?: string | null;
    ex_dividend_date?: string | null;
    beta?: string | null;
    profit_margin?: string | null;
    operating_margin_ttm?: string | null;
    return_on_assets_ttm?: string | null;
    return_on_equity_ttm?: string | null;
    revenue_ttm?: string | null;
    gross_profit_ttm?: string | null;
    diluted_eps_ttm?: string | null;
    analyst_target_price?: string | null;
    trailing_pe?: string | null;
    forward_pe?: string | null;
    price_to_sales_ratio_ttm?: string | null;
    price_to_book_ratio?: string | null;
    ev_to_revenue?: string | null;
    ev_to_ebitda?: string | null;
    last_updated?: string;
  };
}