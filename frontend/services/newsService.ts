// News service for fetching news data

import {
  NewsArticle,
  StockNewsResponse,
  StockSentiment,
  TrendingNewsResponse,
  MarketNewsResponse,
  AllNewsResponse,
  AllNewsParams,
  NewsSource,
  DailyNewsKeywordResponse,
  RecommendationsResponse,
  StockInsightsResponse,
} from '@/types/news';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const newsService = {
  /**
   * Get news articles for a specific stock
   * @param symbol - Stock symbol (e.g., "AAPL")
   * @param days - Number of days to look back (default: 7)
   * @param refresh - Force refresh from API (default: false)
   */
  async getStockNews(
    symbol: string,
    days: number = 7,
    refresh: boolean = false
  ): Promise<StockNewsResponse> {
    const params = new URLSearchParams({
      days: days.toString(),
      refresh: refresh.toString(),
    });

    const response = await fetch(`${API_URL}/news/stock/${symbol}/?${params}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch stock news');
    }

    return response.json();
  },

  /**
   * Get sentiment analysis for a specific stock
   * @param symbol - Stock symbol (e.g., "AAPL")
   * @param days - Number of days to look back (default: 7)
   */
  async getStockSentiment(
    symbol: string,
    days: number = 7
  ): Promise<StockSentiment> {
    const params = new URLSearchParams({
      days: days.toString(),
    });

    const response = await fetch(`${API_URL}/news/stock/${symbol}/sentiment/?${params}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch stock sentiment');
    }

    return response.json();
  },

  /**
   * Get trending news stocks
   * @param timeframe - Time period (e.g., "24h", "7d", "30d")
   * @param limit - Maximum number of results (default: 10)
   */
  async getTrendingNews(
    timeframe: string = '24h',
    limit: number = 10
  ): Promise<TrendingNewsResponse> {
    const params = new URLSearchParams({
      timeframe,
      limit: limit.toString(),
    });

    const response = await fetch(`${API_URL}/news/trending/?${params}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch trending news');
    }

    return response.json();
  },

  /**
   * Get detailed news article by UUID
   * @param uuid - News article UUID
   */
  async getNewsDetail(uuid: string): Promise<NewsArticle> {
    const response = await fetch(`${API_URL}/news/${uuid}/`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch news detail');
    }

    return response.json();
  },

  /**
   * Get market-wide news
   * @param category - News category (general, forex, crypto, merger)
   * @param limit - Maximum number of results (default: 20)
   * @param refresh - Force refresh from API (default: false)
   */
  async getMarketNews(
    category: string = 'general',
    limit: number = 20,
    refresh: boolean = false
  ): Promise<MarketNewsResponse> {
    const params = new URLSearchParams({
      category,
      limit: limit.toString(),
      refresh: refresh.toString(),
    });

    const response = await fetch(`${API_URL}/news/market/?${params}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch market news');
    }

    return response.json();
  },

  // ===== Phase 1: News Page API =====

  /**
   * Get all news with source filtering and pagination
   * @param params - Query parameters (source, category, days, limit, offset, refresh)
   */
  async getAll(params: AllNewsParams = {}): Promise<AllNewsResponse> {
    const queryParams = new URLSearchParams();

    if (params.source) queryParams.set('source', params.source);
    if (params.category) queryParams.set('category', params.category);
    if (params.days) queryParams.set('days', params.days.toString());
    if (params.limit) queryParams.set('limit', params.limit.toString());
    if (params.offset) queryParams.set('offset', params.offset.toString());
    if (params.refresh) queryParams.set('refresh', 'true');

    const response = await fetch(`${API_URL}/news/all/?${queryParams}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch all news');
    }

    return response.json();
  },

  /**
   * Get available news sources with counts
   */
  async getSources(): Promise<NewsSource[]> {
    const response = await fetch(`${API_URL}/news/sources/`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch news sources');
    }

    return response.json();
  },

  // ===== Phase 2: Daily Keywords API =====

  /**
   * Get daily news keywords extracted by LLM
   * @param date - Date in YYYY-MM-DD format (default: today)
   */
  async getDailyKeywords(date?: string): Promise<DailyNewsKeywordResponse> {
    const params = new URLSearchParams();
    if (date) params.set('date', date);

    const response = await fetch(`${API_URL}/news/daily-keywords/?${params}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch daily keywords');
    }

    return response.json();
  },

  // ===== Phase 3.1: Stock Insights API (Fact-Based) =====

  /**
   * Get stock insights based on news mentions (fact-based, no scores)
   * @param date - Date in YYYY-MM-DD format (default: today)
   * @param limit - Maximum number of insights (default: 10)
   * @param includeMarketData - Include market data in response (default: true)
   */
  async getInsights(
    date?: string,
    limit: number = 10,
    includeMarketData: boolean = true
  ): Promise<StockInsightsResponse> {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    params.set('limit', limit.toString());
    params.set('include_market_data', includeMarketData.toString());

    const response = await fetch(`${API_URL}/news/insights/?${params}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch stock insights');
    }

    return response.json();
  },

  // ===== Phase 3: Stock Recommendations API (Legacy) =====

  /**
   * Get stock recommendations based on news keywords
   * @deprecated Use getInsights() instead for fact-based information
   * @param date - Date in YYYY-MM-DD format (default: today)
   * @param limit - Maximum number of recommendations (default: 10)
   */
  async getRecommendations(
    date?: string,
    limit: number = 10
  ): Promise<RecommendationsResponse> {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    params.set('limit', limit.toString());

    const response = await fetch(`${API_URL}/news/recommendations/?${params}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch recommendations');
    }

    return response.json();
  },
};
