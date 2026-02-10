// Stock recommendations section component

'use client';

import React from 'react';
import { Lightbulb, RefreshCw, AlertCircle, Clock, TrendingUp } from 'lucide-react';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import RecommendationCard from './RecommendationCard';
import { useNewsRecommendations } from '@/hooks/useNews';

interface StockRecommendationsProps {
  date?: string;
  limit?: number;
}

// Loading skeleton
function RecommendationSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 animate-pulse">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700" />
        <div className="flex-1 space-y-2">
          <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-20" />
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32" />
        </div>
        <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      </div>
      <div className="mt-3 flex gap-2">
        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded-full w-16" />
        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded-full w-20" />
      </div>
    </div>
  );
}

export default function StockRecommendations({
  date,
  limit = 10,
}: StockRecommendationsProps) {
  const { data, isLoading, error, refetch, isFetching } = useNewsRecommendations(date, limit);

  // Format date for display
  const displayDate = date
    ? format(new Date(date), 'yyyy년 M월 d일', { locale: ko })
    : format(new Date(), 'yyyy년 M월 d일', { locale: ko });

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
            <Lightbulb className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              AI 추천 종목
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {displayDate} 뉴스 기반
            </p>
          </div>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Loading state */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <RecommendationSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && (
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 py-4">
            <AlertCircle className="w-4 h-4" />
            <span>추천 종목을 불러올 수 없습니다</span>
          </div>
        )}

        {/* Empty state */}
        {data?.recommendations && data.recommendations.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-full mb-3">
              <TrendingUp className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              오늘의 추천 종목이 없습니다
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              뉴스 데이터가 충분히 수집된 후 추천이 생성됩니다
            </p>
          </div>
        )}

        {/* Recommendations list */}
        {data?.recommendations && data.recommendations.length > 0 && !isLoading && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {data.recommendations.map((rec, index) => (
                <RecommendationCard
                  key={rec.symbol}
                  recommendation={rec}
                  rank={index + 1}
                />
              ))}
            </div>

            {/* Stats footer */}
            <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
              <div className="flex items-center gap-4">
                {data.total_keywords > 0 && (
                  <span>분석 키워드: {data.total_keywords}개</span>
                )}
                {data.computation_time_ms && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {data.computation_time_ms}ms
                  </span>
                )}
              </div>
              {data.fallback && (
                <span className="text-amber-600 dark:text-amber-400">
                  멘션 기반 추천
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
