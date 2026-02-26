'use client';

import { useState } from 'react';
import { useEODDashboard } from '@/hooks/useEODDashboard';
import { DataFreshnessBadge } from '@/components/eod/DataFreshnessBadge';
import { MarketSummaryBar } from '@/components/eod/MarketSummaryBar';
import { SignalFilterTabs } from '@/components/eod/SignalFilterTabs';
import { SignalCardGrid } from '@/components/eod/SignalCardGrid';
import { SignalDetailSheet } from '@/components/eod/SignalDetailSheet';
import { EODSkeleton } from '@/components/eod/EODSkeleton';
import type { SignalCategory, SignalCard } from '@/types/eod';

export default function Home() {
  const { data, isLoading, error } = useEODDashboard();
  const [activeCategory, setActiveCategory] = useState<SignalCategory | 'all'>('all');
  const [selectedCard, setSelectedCard] = useState<SignalCard | null>(null);

  if (isLoading) return <EODSkeleton />;

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center px-4">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            데이터를 불러올 수 없습니다
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            아직 시그널 데이터가 생성되지 않았거나 네트워크 오류입니다.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            새로고침
          </button>
        </div>
      </div>
    );
  }

  const filteredCards = activeCategory === 'all'
    ? data.signal_cards
    : data.signal_cards.filter((card) => card.category === activeCategory);

  return (
    <div className="min-h-screen pb-20 md:pb-0">
      <div className="max-w-6xl mx-auto px-4 py-4">
        {/* Level 1: 데이터 신선도 */}
        <DataFreshnessBadge
          tradingDate={data.trading_date}
          generatedAt={data.generated_at}
          isStale={data.is_stale}
        />

        {/* Level 2: 시장 요약 */}
        <MarketSummaryBar summary={data.market_summary} />

        {/* Level 3: 카테고리 필터 */}
        <SignalFilterTabs
          cards={data.signal_cards}
          activeCategory={activeCategory}
          onCategoryChange={setActiveCategory}
        />

        {/* Level 4: 시그널 카드 그리드 */}
        <SignalCardGrid
          cards={filteredCards}
          onCardClick={(card) => setSelectedCard(card)}
        />
      </div>

      {/* 시그널 상세 시트 */}
      {selectedCard && (
        <SignalDetailSheet
          card={selectedCard}
          onClose={() => setSelectedCard(null)}
        />
      )}
    </div>
  );
}
