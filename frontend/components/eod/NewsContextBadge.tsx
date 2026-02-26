'use client';

import { Newspaper, ClipboardList, Info } from 'lucide-react';
import type { NewsContext } from '@/types/eod';

interface NewsContextBadgeProps {
  news: NewsContext;
}

const MATCH_TYPE_CONFIG = {
  symbol_today: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-800 dark:text-blue-200',
    border: 'border-blue-200 dark:border-blue-700',
    fontWeight: 'font-semibold',
    italic: false,
    prefix: '',
    icon: Newspaper,
  },
  symbol_7d: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-blue-100 dark:border-blue-800',
    fontWeight: 'font-medium',
    italic: false,
    prefix: '',
    icon: Newspaper,
  },
  symbol_30d: {
    bg: 'bg-gray-100 dark:bg-gray-700/50',
    text: 'text-gray-500 dark:text-gray-400',
    border: 'border-gray-200 dark:border-gray-600',
    fontWeight: 'font-normal',
    italic: false,
    prefix: '',
    icon: Newspaper,
  },
  industry_7d: {
    bg: 'bg-purple-50 dark:bg-purple-900/20',
    text: 'text-purple-600 dark:text-purple-400',
    border: 'border-purple-200 dark:border-purple-700',
    fontWeight: 'font-normal',
    italic: true,
    prefix: '배경: ',
    icon: ClipboardList,
  },
  profile: {
    bg: 'bg-gray-50 dark:bg-gray-800',
    text: 'text-gray-500 dark:text-gray-400',
    border: 'border-gray-200 dark:border-gray-700',
    fontWeight: 'font-normal',
    italic: false,
    prefix: '',
    icon: Info,
  },
};

export function NewsContextBadge({ news }: NewsContextBadgeProps) {
  const config = MATCH_TYPE_CONFIG[news.match_type] ?? MATCH_TYPE_CONFIG.profile;
  const IconComponent = config.icon;

  const showAge = news.age_days > 0 && ['symbol_7d', 'symbol_30d'].includes(news.match_type);

  return (
    <div
      className={`
        flex items-start gap-1.5 px-2 py-1 rounded-md text-[11px] border
        ${config.bg} ${config.text} ${config.border}
      `}
    >
      <IconComponent className="w-3 h-3 mt-0.5 flex-shrink-0 opacity-70" />
      <span className={`truncate leading-tight ${config.fontWeight} ${config.italic ? 'italic' : ''}`}>
        {config.prefix}
        {news.headline}
        {showAge && (
          <span className="ml-1 opacity-60 not-italic font-normal">
            ({news.age_days}일 전)
          </span>
        )}
      </span>
    </div>
  );
}
