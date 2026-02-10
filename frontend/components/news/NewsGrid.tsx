// News grid layout with responsive columns

'use client';

import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import NewsCard from './NewsCard';
import NewsDetailModal from './NewsDetailModal';
import { NewsListItem } from '@/types/news';

interface NewsGridProps {
  articles: NewsListItem[];
  isLoading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  isLoadingMore?: boolean;
}

// Loading skeleton
function NewsCardSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden animate-pulse">
      <div className="flex gap-4 p-4">
        <div className="w-32 h-24 rounded-lg bg-gray-200 dark:bg-gray-700" />
        <div className="flex-1 space-y-3">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full" />
          <div className="flex gap-2">
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-16" />
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-20" />
          </div>
        </div>
      </div>
    </div>
  );
}

// Empty state
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 mb-4 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
        <svg
          className="w-8 h-8 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
        뉴스가 없습니다
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        선택한 필터에 해당하는 뉴스가 없습니다.
      </p>
    </div>
  );
}

export default function NewsGrid({
  articles,
  isLoading,
  hasMore,
  onLoadMore,
  isLoadingMore,
}: NewsGridProps) {
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);

  // Loading state
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 p-4 sm:p-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <NewsCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  // Empty state
  if (!articles || articles.length === 0) {
    return <EmptyState />;
  }

  return (
    <>
      <div className="p-4 sm:p-6 space-y-4">
        {/* News Grid - Single column for better readability */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {articles.map((article) => (
            <NewsCard
              key={article.id}
              article={article}
              onClick={() => setSelectedArticleId(article.id)}
            />
          ))}
        </div>

        {/* Load More Button */}
        {hasMore && onLoadMore && (
          <div className="flex justify-center pt-4">
            <button
              onClick={onLoadMore}
              disabled={isLoadingMore}
              className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoadingMore ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  로딩 중...
                </>
              ) : (
                '더 보기'
              )}
            </button>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <NewsDetailModal
        newsId={selectedArticleId}
        onClose={() => setSelectedArticleId(null)}
      />
    </>
  );
}
