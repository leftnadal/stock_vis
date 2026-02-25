// Custom hooks for news data fetching with TanStack Query

import { useQuery } from '@tanstack/react-query';
import { newsService } from '@/services/newsService';
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
  MarketFeedResponse,
  InterestOptionsResponse,
  MLStatusResponse,
  MLShadowReportResponse,
  NewsEventsResponse,
  MLWeeklyReportResponse,
  LightGBMReadinessResponse,
} from '@/types/news';

/**
 * Hook to fetch stock news articles
 */
export function useStockNews(symbol: string, days: number = 7, refresh: boolean = false) {
  return useQuery<StockNewsResponse>({
    queryKey: ['stock-news', symbol, days, refresh],
    queryFn: () => newsService.getStockNews(symbol, days, refresh),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 5, // 5 minutes
    retry: 2,
  });
}

/**
 * Hook to fetch stock sentiment analysis
 */
export function useStockSentiment(symbol: string, days: number = 7) {
  return useQuery<StockSentiment>({
    queryKey: ['stock-sentiment', symbol, days],
    queryFn: () => newsService.getStockSentiment(symbol, days),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 10, // 10 minutes
    retry: 2,
  });
}

/**
 * Hook to fetch trending news stocks
 */
export function useTrendingNews(timeframe: string = '24h', limit: number = 10) {
  return useQuery<TrendingNewsResponse>({
    queryKey: ['trending-news', timeframe, limit],
    queryFn: () => newsService.getTrendingNews(timeframe, limit),
    staleTime: 1000 * 60 * 15, // 15 minutes
    retry: 2,
  });
}

/**
 * Hook to fetch detailed news article
 */
export function useNewsDetail(uuid: string | null) {
  return useQuery<NewsArticle>({
    queryKey: ['news-detail', uuid],
    queryFn: () => newsService.getNewsDetail(uuid!),
    enabled: !!uuid,
    staleTime: 1000 * 60 * 30, // 30 minutes
    retry: 1,
  });
}

/**
 * Hook to fetch market-wide news
 */
export function useMarketNews(
  category: string = 'general',
  limit: number = 20,
  refresh: boolean = false
) {
  return useQuery<MarketNewsResponse>({
    queryKey: ['market-news', category, limit, refresh],
    queryFn: () => newsService.getMarketNews(category, limit, refresh),
    staleTime: 1000 * 60 * 10, // 10 minutes
    retry: 2,
  });
}

// ===== Phase 1: News Page Hooks =====

/**
 * Hook to fetch all news with filtering and pagination
 */
export function useAllNews(params: AllNewsParams = {}) {
  return useQuery<AllNewsResponse>({
    queryKey: ['all-news', params],
    queryFn: () => newsService.getAll(params),
    staleTime: 1000 * 60 * 5, // 5 minutes
    retry: 2,
  });
}

/**
 * Hook to fetch available news sources
 */
export function useNewsSources() {
  return useQuery<NewsSource[]>({
    queryKey: ['news-sources'],
    queryFn: () => newsService.getSources(),
    staleTime: 1000 * 60 * 60, // 1 hour
    retry: 2,
  });
}

// ===== Phase 2: Daily Keywords Hooks =====

/**
 * Hook to fetch daily news keywords
 */
export function useDailyKeywords(date?: string) {
  return useQuery<DailyNewsKeywordResponse>({
    queryKey: ['daily-keywords', date],
    queryFn: () => newsService.getDailyKeywords(date),
    staleTime: 1000 * 60 * 60, // 1 hour (keywords don't change frequently)
    retry: 2,
  });
}

// ===== Phase 3.1: Stock Insights Hooks (Fact-Based) =====

/**
 * Hook to fetch news-based stock insights (fact-based, no scores)
 */
export function useStockInsights(
  date?: string,
  limit: number = 10,
  includeMarketData: boolean = true
) {
  return useQuery<StockInsightsResponse>({
    queryKey: ['stock-insights', date, limit, includeMarketData],
    queryFn: () => newsService.getInsights(date, limit, includeMarketData),
    staleTime: 1000 * 60 * 30, // 30 minutes
    retry: 2,
  });
}

// ===== Phase 3: Stock Recommendations Hooks (Legacy) =====

/**
 * Hook to fetch news-based stock recommendations
 * @deprecated Use useStockInsights() instead for fact-based information
 */
export function useNewsRecommendations(date?: string, limit: number = 10) {
  return useQuery<RecommendationsResponse>({
    queryKey: ['news-recommendations', date, limit],
    queryFn: () => newsService.getRecommendations(date, limit),
    staleTime: 1000 * 60 * 30, // 30 minutes
    retry: 2,
  });
}

// ===== Phase A: Market Feed Hook (Cold Start) =====

/**
 * Hook to fetch market feed for unauthenticated / cold-start users
 * Includes AI briefing keywords, sector performance, and hot movers
 */
export function useMarketFeed() {
  return useQuery<MarketFeedResponse>({
    queryKey: ['market-feed'],
    queryFn: () => newsService.getMarketFeed(),
    staleTime: 1000 * 60 * 10, // 10분
    retry: 2,
  });
}

// ===== Phase B: Interest Options Hook =====

/**
 * Hook to fetch available interest options (themes + sectors) for onboarding
 */
export function useInterestOptions() {
  return useQuery<InterestOptionsResponse>({
    queryKey: ['interest-options'],
    queryFn: () => newsService.getInterestOptions(),
    staleTime: 1000 * 60 * 60, // 1시간
    retry: 2,
  });
}

// ===== Phase 4: ML Model Status Hooks =====

/**
 * Hook to fetch ML model current status
 */
export function useMLStatus() {
  return useQuery<MLStatusResponse>({
    queryKey: ['ml-status'],
    queryFn: () => newsService.getMLStatus(),
    staleTime: 1000 * 60 * 5, // 5분
    retry: 1,
  });
}

/**
 * Hook to fetch ML shadow mode comparison report
 */
export function useMLShadowReport() {
  return useQuery<MLShadowReportResponse>({
    queryKey: ['ml-shadow-report'],
    queryFn: () => newsService.getMLShadowReport(),
    staleTime: 1000 * 60 * 10, // 10분
    retry: 1,
  });
}

/**
 * Hook to fetch news events for a symbol (Neo4j)
 */
export function useNewsEvents(symbol: string, days: number = 7) {
  return useQuery<NewsEventsResponse>({
    queryKey: ['news-events', symbol, days],
    queryFn: () => newsService.getNewsEvents(symbol, days),
    enabled: !!symbol,
    staleTime: 1000 * 60 * 5, // 5분
    retry: 1,
  });
}

// ===== Phase 5: ML Weekly Report Hook =====

/**
 * Hook to fetch ML weekly performance report
 */
export function useMLWeeklyReport() {
  return useQuery<MLWeeklyReportResponse>({
    queryKey: ['ml-weekly-report'],
    queryFn: () => newsService.getMLWeeklyReport(),
    staleTime: 1000 * 60 * 60, // 1시간
    retry: 1,
  });
}

// ===== Phase 6: LightGBM Readiness Hook =====

/**
 * Hook to check LightGBM transition readiness
 */
export function useLightGBMReadiness() {
  return useQuery<LightGBMReadinessResponse>({
    queryKey: ['lightgbm-readiness'],
    queryFn: () => newsService.getLightGBMReadiness(),
    staleTime: 1000 * 60 * 30, // 30분
    retry: 1,
  });
}
