// Keyword badge component with sentiment coloring

'use client';

import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { DailyKeyword } from '@/types/news';

interface KeywordBadgeProps {
  keyword: DailyKeyword;
  onClick?: () => void;
  size?: 'sm' | 'md' | 'lg';
  showSymbols?: boolean;
}

const SENTIMENT_STYLES = {
  positive: {
    bg: 'bg-green-50 dark:bg-green-900/20',
    border: 'border-green-200 dark:border-green-800',
    text: 'text-green-700 dark:text-green-300',
    icon: TrendingUp,
    iconColor: 'text-green-500',
  },
  negative: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    border: 'border-red-200 dark:border-red-800',
    text: 'text-red-700 dark:text-red-300',
    icon: TrendingDown,
    iconColor: 'text-red-500',
  },
  neutral: {
    bg: 'bg-gray-50 dark:bg-gray-800',
    border: 'border-gray-200 dark:border-gray-700',
    text: 'text-gray-700 dark:text-gray-300',
    icon: Minus,
    iconColor: 'text-gray-400',
  },
};

const SIZE_STYLES = {
  sm: {
    padding: 'px-2 py-1',
    text: 'text-xs',
    icon: 'w-3 h-3',
    gap: 'gap-1',
  },
  md: {
    padding: 'px-3 py-1.5',
    text: 'text-sm',
    icon: 'w-4 h-4',
    gap: 'gap-1.5',
  },
  lg: {
    padding: 'px-4 py-2',
    text: 'text-base',
    icon: 'w-5 h-5',
    gap: 'gap-2',
  },
};

export default function KeywordBadge({
  keyword,
  onClick,
  size = 'md',
  showSymbols = false,
}: KeywordBadgeProps) {
  const sentiment = keyword.sentiment || 'neutral';
  const styles = SENTIMENT_STYLES[sentiment as keyof typeof SENTIMENT_STYLES] ?? SENTIMENT_STYLES.neutral;
  const sizeStyles = SIZE_STYLES[size];
  const Icon = styles.icon;

  return (
    <button
      onClick={onClick}
      title={keyword.reason || undefined}
      className={`
        inline-flex items-center ${sizeStyles.gap} ${sizeStyles.padding}
        ${styles.bg} ${styles.border} border rounded-full
        ${sizeStyles.text} font-medium
        hover:shadow-sm transition-shadow
        ${onClick ? 'cursor-pointer' : 'cursor-default'}
      `}
    >
      <Icon className={`${sizeStyles.icon} ${styles.iconColor}`} />
      <span className={styles.text}>{keyword.text}</span>

      {/* Related Symbols */}
      {showSymbols && keyword.related_symbols && keyword.related_symbols.length > 0 && (
        <span className="text-gray-400 dark:text-gray-500">
          ({keyword.related_symbols.slice(0, 2).join(', ')})
        </span>
      )}

      {/* Importance indicator */}
      {keyword.importance && keyword.importance > 0.8 && (
        <span className="w-1.5 h-1.5 bg-yellow-400 rounded-full" title="중요 키워드" />
      )}
    </button>
  );
}
