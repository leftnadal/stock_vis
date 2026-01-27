// Custom hooks for news data fetching with TanStack Query

import { useQuery } from '@tanstack/react-query';
import { newsService } from '@/services/newsService';
import {
  NewsArticle,
  StockNewsResponse,
  StockSentiment,
  TrendingNewsResponse,
  MarketNewsResponse,
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
