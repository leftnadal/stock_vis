'use client';

import { useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { useExplorationStore } from '@/lib/stores/explorationStore';
import { useSeedData } from '@/hooks/useMarketView';
import SectorBar from '@/components/chainsight/SectorBar';
import MarketGraphCanvas from '@/components/chainsight/MarketGraphCanvas';
import ExplorationTrail from '@/components/chainsight/ExplorationTrail';
import RelationCardPanel from '@/components/chainsight/RelationCardPanel';
import ChainStoryFeed from '@/components/chainsight/ChainStoryFeed';

export default function ChainSightPage() {
  const params = useSearchParams();
  const focusSymbol = params.get('focus');

  const { data: seedData, isLoading } = useSeedData();
  const state = useExplorationStore();

  // ?focus=NVDA 처리: 전용 초기화 액션으로 원자적 처리
  useEffect(() => {
    if (focusSymbol && seedData) {
      const stock = seedData.seeds.find((s) => s.symbol === focusSymbol.toUpperCase());
      if (stock) {
        state.initializeFocusExploration(stock.sector, stock.symbol);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusSymbol, seedData]);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-[200px]">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-4 space-y-4">
      {/* ① 섹터 바 */}
      <SectorBar sectors={seedData?.sector_summary || []} />

      {/* ② 그래프 캔버스 */}
      <MarketGraphCanvas />

      {/* ③ 탐색 트레일 */}
      <ExplorationTrail />

      {/* ④ 관계 카드 패널 */}
      <RelationCardPanel />

      {/* ⑤ 체인 스토리 피드 */}
      <ChainStoryFeed />
    </div>
  );
}
