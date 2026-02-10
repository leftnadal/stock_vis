// News filter bar with category and time filters

'use client';

import React from 'react';
import { Filter, Clock } from 'lucide-react';
import { MarketNewsCategory } from '@/types/news';

type CategoryFilter = MarketNewsCategory | 'all';
type TimeFilter = 1 | 7 | 30;

interface NewsFilterBarProps {
  activeCategory: CategoryFilter;
  activeTime: TimeFilter;
  onCategoryChange: (category: CategoryFilter) => void;
  onTimeChange: (days: TimeFilter) => void;
  totalCount?: number;
}

const CATEGORIES: { value: CategoryFilter; label: string }[] = [
  { value: 'all', label: '전체' },
  { value: 'general', label: 'General' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'forex', label: 'Forex' },
  { value: 'merger', label: 'M&A' },
];

const TIME_OPTIONS: { value: TimeFilter; label: string }[] = [
  { value: 1, label: '24시간' },
  { value: 7, label: '7일' },
  { value: 30, label: '30일' },
];

export default function NewsFilterBar({
  activeCategory,
  activeTime,
  onCategoryChange,
  onTimeChange,
  totalCount,
}: NewsFilterBarProps) {
  return (
    <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Category Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <div className="flex gap-1">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                onClick={() => onCategoryChange(cat.value)}
                className={`
                  px-3 py-1.5 text-sm rounded-full transition-colors
                  ${
                    activeCategory === cat.value
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
                  }
                `}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Right side: Time filter + Count */}
        <div className="flex items-center gap-4">
          {/* Time Filter */}
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-gray-400" />
            <div className="flex gap-1">
              {TIME_OPTIONS.map((time) => (
                <button
                  key={time.value}
                  onClick={() => onTimeChange(time.value)}
                  className={`
                    px-3 py-1.5 text-sm rounded-full transition-colors
                    ${
                      activeTime === time.value
                        ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
                    }
                  `}
                >
                  {time.label}
                </button>
              ))}
            </div>
          </div>

          {/* Total Count */}
          {typeof totalCount === 'number' && (
            <span className="text-sm text-gray-500 dark:text-gray-400">
              총 {totalCount.toLocaleString()}개
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
