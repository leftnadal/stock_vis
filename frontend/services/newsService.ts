// News service for fetching news data

import { API_BASE_URL } from '@/lib/api/config'
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
  KeywordDetailResponse,
  RecommendationsResponse,
  StockInsightsResponse,
  MarketFeedResponse,
  InterestOptionsResponse,
  MLStatusResponse,
  MLShadowReportResponse,
  NewsEventsResponse,
  MLWeeklyReportResponse,
  LightGBMReadinessResponse,
} from '@/types/news';
// NEWS-AUTH (2026-06-12): 파생 자산(종목 상세·추천)은 인증 유지 → authAxios(JWT 동반).
// 공개 read(all/daily-keywords/trending/sources/insights/news-events)는 raw fetch 유지(AllowAny).
import { authAxios } from '@/lib/api/authAxios';

const API_URL = API_BASE_URL;

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
    // 인증 유지 (파생 자산) — authAxios로 JWT 동반
    const { data } = await authAxios.get<StockNewsResponse>(
      `/news/stock/${symbol}/`,
      { params: { days, refresh } }
    );
    return data;
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
    // 인증 유지 (파생 자산) — authAxios로 JWT 동반
    const { data } = await authAxios.get<StockSentiment>(
      `/news/stock/${symbol}/sentiment/`,
      { params: { days } }
    );
    return data;
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

  // ===== Phase 2.5: Keyword Detail API =====

  /**
   * Get keyword detail with related articles and LLM analysis
   * @param date - Date in YYYY-MM-DD format
   * @param index - Keyword index (0-based)
   */
  async getKeywordDetail(date: string, index: number): Promise<KeywordDetailResponse> {
    const params = new URLSearchParams({
      date,
      index: index.toString(),
    });
    const response = await fetch(`${API_URL}/news/keyword-detail/?${params}`, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to fetch keyword detail');
    return response.json();
  },

  // ===== Phase 3.1: Stock Insights API (Fact-Based) =====

  /**
   * Get stock insights based on news mentions (fact-based, no scores)
   * @param date - Date in YYYY-MM-DD format (default: today)
   * @param limit - Maximum number of insights (default: 10)
   * @param includeMarketData - Include market data in response (default: true)
   * @param sector - Filter by sector name (default: undefined = all sectors)
   */
  async getInsights(
    date?: string,
    limit: number = 10,
    includeMarketData: boolean = true,
    sector?: string
  ): Promise<StockInsightsResponse> {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    params.set('limit', limit.toString());
    params.set('include_market_data', includeMarketData.toString());
    if (sector) params.set('sector', sector);

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
    // 인증 유지 (파생 자산) — authAxios로 JWT 동반
    const params: Record<string, string | number> = { limit };
    if (date) params.date = date;
    const { data } = await authAxios.get<RecommendationsResponse>(
      '/news/recommendations/',
      { params }
    );
    return data;
  },

  // ===== Phase A: Market Feed (Cold Start) =====

  /**
   * Get market feed for unauthenticated / cold-start users
   * AllowAny endpoint — no auth header required
   */
  async getMarketFeed(): Promise<MarketFeedResponse> {
    const response = await fetch(`${API_URL}/news/market-feed/`, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to fetch market feed');
    return response.json();
  },

  // ===== Phase B: Interest Options =====

  /**
   * Get available interest options (themes + sectors) for onboarding
   * AllowAny endpoint — no auth header required
   */
  async getInterestOptions(): Promise<InterestOptionsResponse> {
    const response = await fetch(`${API_URL}/news/interest-options/`, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to fetch interest options');
    return response.json();
  },

  // ===== Phase 4: ML Model Status API =====

  async getMLStatus(): Promise<MLStatusResponse> {
    const response = await fetch(`${API_URL}/news/ml-status/`, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to fetch ML status');
    return response.json();
  },

  async getMLShadowReport(): Promise<MLShadowReportResponse> {
    const response = await fetch(`${API_URL}/news/ml-shadow-report/`, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to fetch ML shadow report');
    return response.json();
  },

  // ===== Phase 4: News Events API =====

  async getNewsEvents(symbol: string, days: number = 7): Promise<NewsEventsResponse> {
    const params = new URLSearchParams({
      symbol,
      days: days.toString(),
    });
    const response = await fetch(`${API_URL}/news/news-events/?${params}`, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to fetch news events');
    return response.json();
  },

  // ===== Phase 5: ML Weekly Report API =====

  async getMLWeeklyReport(): Promise<MLWeeklyReportResponse> {
    const response = await fetch(`${API_URL}/news/ml-weekly-report/`, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to fetch ML weekly report');
    return response.json();
  },

  // ===== Phase 6: LightGBM Readiness API =====

  async getLightGBMReadiness(): Promise<LightGBMReadinessResponse> {
    const response = await fetch(`${API_URL}/news/ml-lightgbm-readiness/`, {
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to fetch LightGBM readiness');
    return response.json();
  },
};
