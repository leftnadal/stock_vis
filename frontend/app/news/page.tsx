'use client';

import React, { useState, useCallback } from 'react';
import { AlertCircle } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import NewsHeader from '@/components/news/NewsHeader';
import NewsFilterBar from '@/components/news/NewsFilterBar';
import NewsGrid from '@/components/news/NewsGrid';
import DailyKeywordCard from '@/components/news/DailyKeywordCard';
import NewsHighlightedStocks from '@/components/news/NewsHighlightedStocks';
import { useAllNews, useNewsSources } from '@/hooks/useNews';
import { newsService } from '@/services/newsService';
import { DailyKeyword } from '@/types/news';
import { NewsSourceType, MarketNewsCategory, AllNewsParams } from '@/types/news';

type CategoryFilter = MarketNewsCategory | 'all';
type TimeFilter = 1 | 7 | 30;

const DEFAULT_LIMIT = 20;

export default function NewsPage() {
  // Filter states
  const [activeSource, setActiveSource] = useState<NewsSourceType>('all');
  const [activeCategory, setActiveCategory] = useState<CategoryFilter>('all');
  const [activeTime, setActiveTime] = useState<TimeFilter>(30);
  const [offset, setOffset] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const queryClient = useQueryClient();

  // Build query params
  const queryParams: AllNewsParams = {
    source: activeSource,
    category: activeCategory,
    days: activeTime,
    limit: DEFAULT_LIMIT,
    offset: offset,
  };

  // Fetch data
  const {
    data: sourcesData,
    isLoading: sourcesLoading,
  } = useNewsSources();

  const {
    data: newsData,
    isLoading: newsLoading,
    isFetching,
    error,
    refetch,
  } = useAllNews(queryParams);

  // Default sources if loading
  const sources = sourcesData || [
    { name: 'all' as const, label: '전체', count: 0 },
    { name: 'finnhub' as const, label: 'Finnhub', count: 0 },
    { name: 'marketaux' as const, label: 'Marketaux', count: 0 },
  ];

  // Handle filter changes - reset offset
  const handleSourceChange = useCallback((source: NewsSourceType) => {
    setActiveSource(source);
    setOffset(0);
  }, []);

  const handleCategoryChange = useCallback((category: CategoryFilter) => {
    setActiveCategory(category);
    setOffset(0);
  }, []);

  const handleTimeChange = useCallback((days: TimeFilter) => {
    setActiveTime(days);
    setOffset(0);
  }, []);

  // Handle load more
  const handleLoadMore = useCallback(() => {
    setOffset((prev) => prev + DEFAULT_LIMIT);
  }, []);

  // Handle refresh - fetch new news from external APIs
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    setOffset(0);

    try {
      // Call API with refresh=true to fetch new news from external sources
      await newsService.getAll({
        source: activeSource,
        category: activeCategory,
        days: activeTime,
        limit: DEFAULT_LIMIT,
        offset: 0,
        refresh: true,
      });

      // Invalidate cache and refetch
      queryClient.invalidateQueries({ queryKey: ['all-news'] });
      queryClient.invalidateQueries({ queryKey: ['news-sources'] });
    } catch (error) {
      console.error('Failed to refresh news:', error);
    } finally {
      setIsRefreshing(false);
    }
  }, [activeSource, activeCategory, activeTime, queryClient]);

  // Combine articles when loading more
  const [allArticles, setAllArticles] = React.useState(newsData?.articles || []);

  React.useEffect(() => {
    if (newsData?.articles) {
      if (offset === 0) {
        // Reset when filters change
        setAllArticles(newsData.articles);
      } else {
        // Append when loading more
        setAllArticles((prev) => {
          const existingIds = new Set(prev.map((a) => a.id));
          const newArticles = newsData.articles.filter((a) => !existingIds.has(a.id));
          return [...prev, ...newArticles];
        });
      }
    }
  }, [newsData?.articles, offset]);

  // Reset articles when filters change
  React.useEffect(() => {
    setAllArticles([]);
  }, [activeSource, activeCategory, activeTime]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header with source tabs */}
      <NewsHeader
        sources={sources}
        activeSource={activeSource}
        onSourceChange={handleSourceChange}
        isLoading={isRefreshing || isFetching}
        onRefresh={handleRefresh}
      />

      {/* Filter bar */}
      <NewsFilterBar
        activeCategory={activeCategory}
        activeTime={activeTime}
        onCategoryChange={handleCategoryChange}
        onTimeChange={handleTimeChange}
        totalCount={newsData?.total}
      />

      {/* News Insights Section - Keywords and Mentioned Stocks */}
      <div className="px-4 sm:px-6 py-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Daily Keywords */}
        <DailyKeywordCard
          onKeywordClick={(keyword: DailyKeyword) => {
            // TODO: Search news by keyword
            console.log('Keyword clicked:', keyword);
          }}
        />

        {/* News Highlighted Stocks (fact-based, no scores) */}
        <NewsHighlightedStocks limit={6} />
      </div>

      {/* Error state */}
      {error && (
        <div className="mx-4 sm:mx-6 mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                뉴스를 불러오는데 실패했습니다
              </p>
              <p className="text-sm text-red-600 dark:text-red-400">
                잠시 후 다시 시도해주세요
              </p>
            </div>
          </div>
        </div>
      )}

      {/* News grid */}
      <NewsGrid
        articles={allArticles}
        isLoading={newsLoading && offset === 0}
        hasMore={newsData?.has_more}
        onLoadMore={handleLoadMore}
        isLoadingMore={isFetching && offset > 0}
      />
    </div>
  );
}
