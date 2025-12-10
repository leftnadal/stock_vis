// News detail modal component

'use client';

import React, { useEffect } from 'react';
import Image from 'next/image';
import { format, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';
import { X, ExternalLink, Clock, Building2, AlertCircle } from 'lucide-react';
import SentimentBadge from './SentimentBadge';
import { useNewsDetail } from '@/hooks/useNews';

export interface NewsDetailModalProps {
  newsId: string | null;
  onClose: () => void;
}

export default function NewsDetailModal({ newsId, onClose }: NewsDetailModalProps) {
  const { data: article, isLoading, error } = useNewsDetail(newsId);

  // Close on ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (newsId) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [newsId, onClose]);

  // Don't render if no newsId
  if (!newsId) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
      onClick={onClose}
    >
      {/* Modal Content */}
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">뉴스 상세</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            aria-label="닫기"
          >
            <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto max-h-[calc(90vh-4rem)]">
          {/* Loading State */}
          {isLoading && (
            <div className="p-6 space-y-4">
              <div className="animate-pulse space-y-4">
                <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && !isLoading && (
            <div className="p-6 text-center">
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
              <p className="text-red-600 dark:text-red-400">뉴스 상세 정보를 불러올 수 없습니다</p>
              <button
                onClick={onClose}
                className="mt-4 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              >
                닫기
              </button>
            </div>
          )}

          {/* Article Content */}
          {article && !isLoading && !error && (
            <div className="p-6 space-y-6">
              {/* Image */}
              {article.image_url && (
                <div className="relative w-full h-64 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700">
                  <Image
                    src={article.image_url}
                    alt={article.title}
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 100vw, 768px"
                  />
                </div>
              )}

              {/* Title */}
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {article.title}
              </h1>

              {/* Meta Information */}
              <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                <div className="flex items-center gap-1">
                  <span className="font-medium">{article.source}</span>
                </div>

                <div className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  <span>
                    {format(parseISO(article.published_at), 'yyyy년 MM월 dd일 HH:mm', {
                      locale: ko,
                    })}
                  </span>
                </div>

                {article.category && (
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 rounded text-xs font-medium">
                    {article.category}
                  </span>
                )}

                {article.sentiment_score !== null && (
                  <SentimentBadge score={article.sentiment_score} size="sm" />
                )}
              </div>

              {/* Summary */}
              <div className="prose dark:prose-invert max-w-none">
                <p className="text-gray-700 dark:text-gray-300 leading-relaxed">
                  {article.summary}
                </p>
              </div>

              {/* Related Entities */}
              {article.entities && article.entities.length > 0 && (
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white mb-3">
                    <Building2 className="w-4 h-4" />
                    관련 종목
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {article.entities.map((entity, index) => (
                      <div
                        key={index}
                        className="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm"
                      >
                        <span className="font-medium text-gray-900 dark:text-white">
                          {entity.symbol}
                        </span>
                        <span className="text-gray-600 dark:text-gray-400 ml-2">
                          {entity.entity_name}
                        </span>
                        {entity.sentiment_score !== null && (
                          <span className="ml-2">
                            <SentimentBadge
                              score={entity.sentiment_score}
                              size="sm"
                              showLabel={false}
                            />
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Original Link */}
              {article.url && (
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    원문 보기
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
