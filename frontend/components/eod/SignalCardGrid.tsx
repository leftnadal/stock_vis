'use client';

import { Inbox } from 'lucide-react';
import { SignalCard } from './SignalCard';
import type { SignalCard as SignalCardType } from '@/types/eod';

interface SignalCardGridProps {
  cards: SignalCardType[];
  onCardClick: (card: SignalCardType) => void;
  onCategoryChange?: (category: 'all') => void;
}

export function SignalCardGrid({ cards, onCardClick, onCategoryChange }: SignalCardGridProps) {
  if (cards.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Inbox className="w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
        <p className="text-gray-400 dark:text-gray-500 text-sm mb-2">
          해당 카테고리에 시그널이 없습니다.
        </p>
        {onCategoryChange && (
          <button
            onClick={() => onCategoryChange('all')}
            className="text-blue-500 hover:text-blue-600 text-sm font-medium transition-colors"
          >
            전체 시그널 보기
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {cards.map((card) => (
        <SignalCard
          key={card.id}
          card={card}
          onCardClick={onCardClick}
        />
      ))}
    </div>
  );
}
