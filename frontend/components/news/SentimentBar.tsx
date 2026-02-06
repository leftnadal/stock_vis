// Sentiment distribution bar component

'use client';

import React from 'react';
import { SentimentDistribution } from '@/types/news';

interface SentimentBarProps {
  distribution: SentimentDistribution;
  showLabels?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const sizeStyles = {
  sm: 'h-2',
  md: 'h-3',
  lg: 'h-4',
};

export default function SentimentBar({
  distribution,
  showLabels = true,
  size = 'md',
}: SentimentBarProps) {
  const { positive, negative, neutral, total } = distribution;

  // Calculate percentages
  const positivePercent = total > 0 ? (positive / total) * 100 : 0;
  const negativePercent = total > 0 ? (negative / total) * 100 : 0;
  const neutralPercent = total > 0 ? (neutral / total) * 100 : 0;

  // Empty state
  if (total === 0) {
    return (
      <div className="text-sm text-gray-400 dark:text-gray-500">
        뉴스 데이터 없음
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Bar */}
      <div className={`flex w-full rounded-full overflow-hidden ${sizeStyles[size]} bg-gray-100 dark:bg-gray-700`}>
        {/* Positive (Green) */}
        {positivePercent > 0 && (
          <div
            className="bg-green-500 dark:bg-green-400 transition-all duration-300"
            style={{ width: `${positivePercent}%` }}
          />
        )}
        {/* Neutral (Gray) */}
        {neutralPercent > 0 && (
          <div
            className="bg-gray-300 dark:bg-gray-500 transition-all duration-300"
            style={{ width: `${neutralPercent}%` }}
          />
        )}
        {/* Negative (Red) */}
        {negativePercent > 0 && (
          <div
            className="bg-red-500 dark:bg-red-400 transition-all duration-300"
            style={{ width: `${negativePercent}%` }}
          />
        )}
      </div>

      {/* Labels */}
      {showLabels && (
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-3">
            {positive > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500 dark:bg-green-400" />
                <span className="text-green-600 dark:text-green-400">
                  긍정 {positive}건
                </span>
              </span>
            )}
            {neutral > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-500" />
                <span className="text-gray-500 dark:text-gray-400">
                  중립 {neutral}건
                </span>
              </span>
            )}
            {negative > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500 dark:bg-red-400" />
                <span className="text-red-600 dark:text-red-400">
                  부정 {negative}건
                </span>
              </span>
            )}
          </div>
          <span className="text-gray-400 dark:text-gray-500">
            총 {total}건
          </span>
        </div>
      )}
    </div>
  );
}
