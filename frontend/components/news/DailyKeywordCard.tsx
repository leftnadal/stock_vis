// Daily keyword card component showing today's market keywords

'use client';

import React from 'react';
import { Sparkles, RefreshCw, AlertCircle, Clock } from 'lucide-react';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import KeywordBadge from './KeywordBadge';
import { useDailyKeywords } from '@/hooks/useNews';
import { DailyKeyword } from '@/types/news';

interface DailyKeywordCardProps {
  date?: string;
  onKeywordClick?: (keyword: DailyKeyword) => void;
}

// Loading skeleton
function KeywordSkeleton() {
  return (
    <div className="flex flex-wrap gap-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="h-8 w-24 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse"
        />
      ))}
    </div>
  );
}

export default function DailyKeywordCard({ date, onKeywordClick }: DailyKeywordCardProps) {
  const { data, isLoading, error, refetch, isFetching } = useDailyKeywords(date);

  // Format date for display
  const displayDate = date
    ? format(new Date(date), 'yyyy년 M월 d일', { locale: ko })
    : format(new Date(), 'yyyy년 M월 d일', { locale: ko });

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
            <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              오늘의 키워드
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {displayDate}
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
        {isLoading && <KeywordSkeleton />}

        {/* Error state */}
        {error && !isLoading && (
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
            <AlertCircle className="w-4 h-4" />
            <span>키워드를 불러올 수 없습니다</span>
          </div>
        )}

        {/* Not found state */}
        {data?.status === 'not_found' && !isLoading && (
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <Clock className="w-4 h-4" />
            <span>키워드가 아직 생성되지 않았습니다</span>
          </div>
        )}

        {/* Failed state */}
        {data?.status === 'failed' && !isLoading && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
              <AlertCircle className="w-4 h-4" />
              <span>키워드 생성 중 문제가 발생했습니다 (기본 키워드 표시)</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {data.keywords?.map((keyword, index) => (
                <KeywordBadge
                  key={index}
                  keyword={keyword}
                  onClick={onKeywordClick ? () => onKeywordClick(keyword) : undefined}
                />
              ))}
            </div>
          </div>
        )}

        {/* Success state */}
        {data?.status === 'completed' && data.keywords && !isLoading && (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {data.keywords.map((keyword, index) => (
                <KeywordBadge
                  key={index}
                  keyword={keyword}
                  onClick={onKeywordClick ? () => onKeywordClick(keyword) : undefined}
                  showSymbols
                />
              ))}
            </div>

            {/* Stats */}
            <div className="flex items-center gap-4 pt-2 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
              <span>분석 뉴스: {data.total_news_count}건</span>
              {data.sources && Object.keys(data.sources).length > 0 && (
                <span>
                  소스: {Object.entries(data.sources)
                    .map(([name, count]) => `${name} ${count}`)
                    .join(', ')}
                </span>
              )}
              {data.llm_model && (
                <span className="ml-auto">
                  {data.llm_model}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
