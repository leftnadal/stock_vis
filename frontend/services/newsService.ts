// News service for fetching news data

import {
  NewsArticle,
  StockNewsResponse,
  StockSentiment,
  TrendingNewsResponse,
  MarketNewsResponse,
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
};
