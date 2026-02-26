'use client';

import { SignalCard } from './SignalCard';
import type { SignalCard as SignalCardType } from '@/types/eod';

interface SignalCardGridProps {
  cards: SignalCardType[];
  onCardClick: (card: SignalCardType) => void;
}

export function SignalCardGrid({ cards, onCardClick }: SignalCardGridProps) {
  if (cards.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-gray-400 dark:text-gray-500 text-sm">
          해당 카테고리에 시그널이 없습니다.
        </p>
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
