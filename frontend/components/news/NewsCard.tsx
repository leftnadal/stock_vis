// News card component for displaying individual news articles

'use client';

import React from 'react';
import Image from 'next/image';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';
import { Clock, ExternalLink } from 'lucide-react';
import SentimentBadge from './SentimentBadge';
import { NewsListItem } from '@/types/news';

export interface NewsCardProps {
  article: NewsListItem;
  onClick?: () => void;
}

export default function NewsCard({ article, onClick }: NewsCardProps) {
  const relativeTime = formatDistanceToNow(new Date(article.published_at), {
    addSuffix: true,
    locale: ko,
  });

  return (
    <div
      onClick={onClick}
      className="bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer border border-gray-200 dark:border-gray-700 overflow-hidden"
    >
      <div className="flex gap-4 p-4">
        {/* Thumbnail Image */}
        <div className="flex-shrink-0">
          {article.image_url ? (
            <div className="relative w-32 h-24 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700">
              <Image
                src={article.image_url}
                alt={article.title}
                fill
                className="object-cover"
                sizes="128px"
                onError={(e) => {
                  // Fallback to placeholder if image fails to load
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                }}
              />
            </div>
          ) : (
            <div className="w-32 h-24 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
              <ExternalLink className="w-8 h-8 text-gray-400" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
            {article.title}
          </h3>

          {/* Summary */}
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
            {article.summary}
          </p>

          {/* Footer: Source, Time, Sentiment */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <span className="font-medium">{article.source}</span>
              <span>•</span>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>{relativeTime}</span>
              </div>
              {(article.entities?.length || article.entity_count || 0) > 0 && (
                <>
                  <span>•</span>
                  <span>{article.entities?.length || article.entity_count}개 종목</span>
                </>
              )}
            </div>

            {/* Sentiment Badge */}
            {article.sentiment_score !== null && (
              <SentimentBadge score={article.sentiment_score} size="sm" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
