// News header with source tabs navigation

'use client';

import React from 'react';
import { Newspaper, RefreshCw } from 'lucide-react';
import { NewsSource, NewsSourceType } from '@/types/news';

interface NewsHeaderProps {
  sources: NewsSource[];
  activeSource: NewsSourceType;
  onSourceChange: (source: NewsSourceType) => void;
  isLoading?: boolean;
  onRefresh?: () => void;
}

export default function NewsHeader({
  sources,
  activeSource,
  onSourceChange,
  isLoading,
  onRefresh,
}: NewsHeaderProps) {
  return (
    <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between px-4 py-4 sm:px-6">
        {/* Title */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
            <Newspaper className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              Market News
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              실시간 시장 뉴스
            </p>
          </div>
        </div>

        {/* Refresh Button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        )}
      </div>

      {/* Source Tabs */}
      <div className="px-4 sm:px-6">
        <nav className="flex gap-1 -mb-px" aria-label="Tabs">
          {sources.map((source) => {
            const isActive = activeSource === source.name;
            return (
              <button
                key={source.name}
                onClick={() => onSourceChange(source.name)}
                className={`
                  px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                  ${
                    isActive
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200'
                  }
                `}
              >
                <span>{source.label}</span>
                <span
                  className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                    isActive
                      ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400'
                      : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                  }`}
                >
                  {source.count}
                </span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
