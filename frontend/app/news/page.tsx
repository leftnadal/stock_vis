'use client';

import React, { useMemo, useCallback, useState } from 'react';
import { AlertCircle, Newspaper, RefreshCw, Clock } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import DailyKeywordCard from '@/components/news/DailyKeywordCard';
import NewsHighlightedStocks from '@/components/news/NewsHighlightedStocks';
import MLModelStatusCard from '@/components/news/MLModelStatusCard';
import AINewsBriefingCard from '@/components/news/AINewsBriefingCard';
import OnboardingBanner from '@/components/news/OnboardingBanner';
import NewsCategorySection from '@/components/news/NewsCategorySection';
import type { NewsCategoryType } from '@/components/news/NewsCategorySection';
import { useAllNews, useNewsSources } from '@/hooks/useNews';
import { useAuth } from '@/contexts/AuthContext';
import { newsService } from '@/services/newsService';
import { DailyKeyword, NewsSourceType, AllNewsParams, NewsListItem } from '@/types/news';

type TimeFilter = 1 | 7 | 30;

const TIME_OPTIONS: { value: TimeFilter; label: string }[] = [
  { value: 1, label: '24시간' },
  { value: 7, label: '7일' },
  { value: 30, label: '30일' },
];

// Category mapping: DB category -> display category
const CATEGORY_MAP: Record<string, NewsCategoryType> = {
  general: 'general',
  'top news': 'general',
  business: 'general',
  'company news': 'general',
  company: 'general',
  crypto: 'crypto',
  forex: 'forex',
  merger: 'merger',
};

const DISPLAY_CATEGORIES: NewsCategoryType[] = ['general', 'crypto', 'forex', 'merger'];

export default function NewsPage() {
  const [activeSource, setActiveSource] = useState<NewsSourceType>('all');
  const [activeTime, setActiveTime] = useState<TimeFilter>(7);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const queryClient = useQueryClient();
  const { user, loading: authLoading } = useAuth();

  // Build query params - fetch ALL news (no category filter), large batch
  const queryParams: AllNewsParams = {
    source: activeSource,
    category: 'all',
    days: activeTime,
    limit: 100,
    offset: 0,
  };

  // Fetch data
  const { data: sourcesData, isLoading: sourcesLoading } = useNewsSources();
  const {
    data: newsData,
    isLoading: newsLoading,
    isFetching,
    error,
  } = useAllNews(queryParams);

  // Default sources
  const sources = sourcesData || [
    { name: 'all' as const, label: '전체', count: 0 },
    { name: 'finnhub' as const, label: 'Finnhub', count: 0 },
    { name: 'marketaux' as const, label: 'Marketaux', count: 0 },
  ];

  // Group articles by category
  const categoryGroups = useMemo(() => {
    const groups: Record<NewsCategoryType, NewsListItem[]> = {
      general: [],
      crypto: [],
      forex: [],
      merger: [],
    };

    const articles = newsData?.articles || [];
    for (const article of articles) {
      const rawCategory = (article.category || 'general').toLowerCase();
      const displayCategory = CATEGORY_MAP[rawCategory] || 'general';
      groups[displayCategory].push(article);
    }

    return groups;
  }, [newsData?.articles]);

  // Total article count
  const totalCount = newsData?.total || 0;

  // Handle source change
  const handleSourceChange = useCallback((source: NewsSourceType) => {
    setActiveSource(source);
  }, []);

  // Handle time change
  const handleTimeChange = useCallback((days: TimeFilter) => {
    setActiveTime(days);
  }, []);

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await newsService.getAll({
        source: activeSource,
        category: 'all',
        days: activeTime,
        limit: 100,
        offset: 0,
        refresh: true,
      });
      queryClient.invalidateQueries({ queryKey: ['all-news'] });
      queryClient.invalidateQueries({ queryKey: ['news-sources'] });
    } catch (err) {
      console.error('Failed to refresh news:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, [activeSource, activeTime, queryClient]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* ─── Header ─── */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
              <Newspaper className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                Market News
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                실시간 시장 뉴스 · {totalCount > 0 ? `총 ${totalCount.toLocaleString()}건` : '로딩 중...'}
              </p>
            </div>
          </div>

          <button
            onClick={handleRefresh}
            disabled={isRefreshing || isFetching}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${isRefreshing || isFetching ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Source Tabs + Time Filter */}
        <div className="px-4 sm:px-6 pb-3 flex items-center justify-between gap-4">
          {/* Source Tabs */}
          <nav className="flex gap-1" aria-label="Source tabs">
            {sources.map((source) => {
              const isActive = activeSource === source.name;
              return (
                <button
                  key={source.name}
                  onClick={() => handleSourceChange(source.name)}
                  className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700'
                  }`}
                >
                  {source.label}
                  <span className={`ml-1.5 text-xs ${isActive ? 'text-blue-500' : 'text-gray-400'}`}>
                    {source.count}
                  </span>
                </button>
              );
            })}
          </nav>

          {/* Time Filter */}
          <div className="flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-gray-400" />
            {TIME_OPTIONS.map((time) => (
              <button
                key={time.value}
                onClick={() => handleTimeChange(time.value)}
                className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
                  activeTime === time.value
                    ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
                }`}
              >
                {time.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ─── Main Content ─── */}
      <div className="px-4 sm:px-6 py-5 space-y-6">
        {/* Onboarding Banner */}
        {!authLoading && user && <OnboardingBanner />}

        {/* ─── Section 1: Intelligence Insights ─── */}
        <section>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-3">
            Intelligence
          </h2>

          {authLoading ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-48 bg-gray-200 dark:bg-gray-700 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : !user ? (
            <AINewsBriefingCard />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <DailyKeywordCard
                onKeywordClick={(keyword: DailyKeyword) => {
                  console.log('Keyword clicked:', keyword);
                }}
              />
              <NewsHighlightedStocks limit={6} />
              <MLModelStatusCard />
            </div>
          )}
        </section>

        {/* ─── Section 2: News by Category ─── */}
        <section>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
            카테고리별 뉴스
          </h2>

          {/* Error state */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
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

          {/* Loading state */}
          {newsLoading && (
            <div className="space-y-6">
              {[1, 2].map((i) => (
                <div key={i} className="space-y-3">
                  <div className="h-6 w-32 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    {[1, 2, 3, 4].map((j) => (
                      <div key={j} className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Category Sections */}
          {!newsLoading && !error && (
            <div className="space-y-8">
              {DISPLAY_CATEGORIES.map((cat) => (
                <NewsCategorySection
                  key={cat}
                  category={cat}
                  articles={categoryGroups[cat]}
                  initialCount={4}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
