'use client';

import { useState } from 'react';
import { useExplorationStore } from '@/lib/stores/explorationStore';
import MarketGraphCanvas from './MarketGraphCanvas';
import RelationCardList from './RelationCardList';

type DrillView = 'list' | 'map';

/**
 * ego 드릴다운 래퍼 (⑳-2 S2/C안).
 * - ego 모드(centerSymbol 존재): [목록][지도] 토글. 기본 = 목록(관계 카드 리스트).
 *   지도 = 기존 그래프 뷰(MarketGraphCanvas) 보존.
 * - 비-ego(섹터/빈 상태): MarketGraphCanvas 그대로(기존 동작 불변).
 */
export default function EgoDrilldown() {
  const { centerSymbol } = useExplorationStore();
  const [view, setView] = useState<DrillView>('list');

  // 비-ego 모드: 기존 그래프 뷰 그대로(섹터 불가·빈 상태 등 MarketGraphCanvas가 처리).
  if (!centerSymbol) {
    return <MarketGraphCanvas />;
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1" role="tablist" aria-label="드릴다운 뷰 전환">
        {(['list', 'map'] as DrillView[]).map((v) => (
          <button
            key={v}
            role="tab"
            aria-selected={view === v}
            onClick={() => setView(v)}
            className={[
              'px-3 py-1 text-xs font-medium rounded-lg border transition',
              view === v
                ? 'border-blue-400 bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                : 'border-gray-200 dark:border-gray-700 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800',
            ].join(' ')}
          >
            {v === 'list' ? '목록' : '지도'}
          </button>
        ))}
      </div>

      {view === 'list' ? <RelationCardList /> : <MarketGraphCanvas />}
    </div>
  );
}
