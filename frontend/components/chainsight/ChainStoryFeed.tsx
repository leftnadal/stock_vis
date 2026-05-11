'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useExplorationStore } from '@/lib/stores/explorationStore';
import { useSignalFeed } from '@/hooks/useMarketView';
import type { ChainSignal } from '@/types/chainsight';

const STRENGTH_COLORS = {
  strong:   'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  moderate: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  weak:     'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
};

const CATEGORY_LABELS: Record<string, string> = {
  supply_chain: '공급망',
  competition: '경쟁',
  co_mention: '동시출현',
  price_correlation: '가격 상관',
  peer_network: '동종 네트워크',
};

export default function ChainStoryFeed() {
  const { startChainExploration, selectSector, setHighlightedChain } = useExplorationStore();
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useSignalFeed();
  const observerRef = useRef<HTMLDivElement>(null);

  // 무한 스크롤
  const handleObserver = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
        fetchNextPage();
      }
    },
    [fetchNextPage, hasNextPage, isFetchingNextPage],
  );

  useEffect(() => {
    const target = observerRef.current;
    if (!target) return;
    const observer = new IntersectionObserver(handleObserver, { threshold: 0.5 });
    observer.observe(target);
    return () => observer.disconnect();
  }, [handleObserver]);

  const chains = data?.pages.flatMap((p) => p.chains) || [];

  if (!chains.length) {
    return (
      <div className="py-6 text-center text-gray-400 text-sm">
        체인 시그널이 없습니다
      </div>
    );
  }

  const handleChainClick = (chain: ChainSignal) => {
    const firstSymbol = chain.path[0]?.symbol;
    const sector = chain.root_sector;
    if (!firstSymbol || !sector) return;

    selectSector(sector);
    startChainExploration(sector, firstSymbol);
    setHighlightedChain(chain.id);
  };

  return (
    <div className="space-y-3 py-4">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
        Chain Story
      </h3>

      {chains.map((chain) => (
        <ChainStoryCard
          key={chain.id}
          chain={chain}
          onClick={() => handleChainClick(chain)}
        />
      ))}

      {/* 무한 스크롤 sentinel */}
      <div ref={observerRef} className="h-4" />
      {isFetchingNextPage && (
        <div className="flex justify-center py-3">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500" />
        </div>
      )}
    </div>
  );
}

function ChainStoryCard({
  chain,
  onClick,
}: {
  chain: ChainSignal;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
    >
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate">
          {chain.title}
        </h4>
        <div className="flex items-center gap-2">
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">
            {CATEGORY_LABELS[chain.category] || chain.category}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${STRENGTH_COLORS[chain.strength]}`}>
            {chain.strength}
          </span>
        </div>
      </div>

      {/* Mini path */}
      <div className="flex items-center gap-1 mb-2 overflow-x-auto">
        {chain.path.map((node, i) => (
          <div key={node.symbol} className="flex items-center gap-1 flex-shrink-0">
            {i > 0 && (
              <span className="text-[10px] text-gray-400">
                →
              </span>
            )}
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 px-1.5 py-0.5 rounded">
              {node.symbol}
            </span>
          </div>
        ))}
      </div>

      {/* 트리거 + confidence */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span className="truncate max-w-[70%]">{chain.trigger_summary}</span>
        <span className="font-medium">
          신뢰도 {chain.total_confidence}
        </span>
      </div>
    </button>
  );
}
