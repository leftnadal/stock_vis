'use client';

import { SIGNAL_CATEGORY_COLORS, SIGNAL_CATEGORY_LABELS } from '@/types/eod';
import type { SignalCard, SignalCategory } from '@/types/eod';

interface SignalFilterTabsProps {
  cards: SignalCard[];
  activeCategory: SignalCategory | 'all';
  onCategoryChange: (category: SignalCategory | 'all') => void;
}

const CATEGORY_ORDER: (SignalCategory | 'all')[] = [
  'all',
  'momentum',
  'volume',
  'breakout',
  'reversal',
  'relation',
  'technical',
];

export function SignalFilterTabs({ cards, activeCategory, onCategoryChange }: SignalFilterTabsProps) {
  // 카테고리별 시그널 수 집계
  const countByCategory = cards.reduce<Record<string, number>>((acc, card) => {
    acc[card.category] = (acc[card.category] || 0) + card.count;
    return acc;
  }, {});

  const totalCount = cards.reduce((sum, card) => sum + card.count, 0);

  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {CATEGORY_ORDER.map((category) => {
          const isActive = activeCategory === category;
          const count = category === 'all' ? totalCount : (countByCategory[category] ?? 0);
          const color = category === 'all' ? '#6B7280' : SIGNAL_CATEGORY_COLORS[category];
          const label = category === 'all' ? '전체' : SIGNAL_CATEGORY_LABELS[category];

          // 해당 카테고리 카드가 없으면 숨김 (전체 제외)
          if (category !== 'all' && count === 0) return null;

          return (
            <button
              key={category}
              onClick={() => onCategoryChange(category)}
              className={`
                flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium
                transition-all duration-150
                ${isActive
                  ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900 shadow-sm'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                }
              `}
            >
              {/* 카테고리 색상 도트 */}
              {!isActive && (
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: color }}
                />
              )}
              <span>{label}</span>
              {/* 카운트 배지 */}
              <span
                className={`
                  inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[11px] font-semibold
                  ${isActive
                    ? 'bg-white/20 dark:bg-black/20 text-white dark:text-gray-900'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                  }
                `}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
