// News highlighted stocks section component (fact-based, no scores)

'use client';

import React from 'react';
import { Newspaper, RefreshCw, AlertCircle, Clock, TrendingUp, CalendarDays } from 'lucide-react';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import StockInsightCard from './StockInsightCard';
import { useStockInsights } from '@/hooks/useNews';

interface NewsHighlightedStocksProps {
  date?: string;
  limit?: number;
}

// Loading skeleton
function InsightSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 animate-pulse">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-16" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24" />
      </div>
      <div className="space-y-2">
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-32" />
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full w-full" />
        <div className="flex gap-2 mt-2">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-12" />
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-12" />
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-12" />
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded-full w-16" />
        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded-full w-20" />
      </div>
    </div>
  );
}

export default function NewsHighlightedStocks({
  date,
  limit = 10,
}: NewsHighlightedStocksProps) {
  const { data, isLoading, error, refetch, isFetching } = useStockInsights(date, limit, true);

  // Format period for display
  const periodLabel = data?.period_days
    ? `최근 ${data.period_days}일`
    : '오늘';
  const periodRange = data?.period_start && data?.period_end
    ? `${format(new Date(data.period_start + 'T00:00:00'), 'M/d', { locale: ko })} ~ ${format(new Date(data.period_end + 'T00:00:00'), 'M/d', { locale: ko })}`
    : '';

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Newspaper className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              뉴스 언급 종목
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <CalendarDays className="w-3 h-3" />
              <span>{periodLabel}</span>
              {periodRange && (
                <span className="text-gray-400 dark:text-gray-500">({periodRange})</span>
              )}
            </p>
          </div>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          title="새로고침"
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
              <InsightSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && (
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 py-4">
            <AlertCircle className="w-4 h-4" />
            <span>종목 인사이트를 불러올 수 없습니다</span>
          </div>
        )}

        {/* Empty state */}
        {data?.insights && data.insights.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-full mb-3">
              <TrendingUp className="w-6 h-6 text-gray-400" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              오늘 뉴스에 언급된 종목이 없습니다
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              뉴스 데이터가 수집된 후 인사이트가 생성됩니다
            </p>
          </div>
        )}

        {/* Insights list */}
        {data?.insights && data.insights.length > 0 && !isLoading && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {data.insights.map((insight) => (
                <StockInsightCard
                  key={insight.symbol}
                  insight={insight}
                  periodLabel={periodLabel}
                />
              ))}
            </div>

            {/* Stats footer */}
            <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
              <div className="flex items-center gap-4">
                {data.total_keywords > 0 && (
                  <span>분석 키워드: {data.total_keywords}개</span>
                )}
                {data.computation_time_ms !== undefined && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {data.computation_time_ms}ms
                  </span>
                )}
              </div>
              <span className="text-gray-400">
                뉴스 언급 횟수 기준 정렬
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
