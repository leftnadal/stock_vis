'use client';

import { Suspense, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { useExplorationStore } from '@/lib/stores/explorationStore';
import { useSeedData } from '@/hooks/useMarketView';
import SectorBar from '@/components/chainsight/SectorBar';
import RelationFilterChips from '@/components/chainsight/RelationFilterChips';
import MarketGraphCanvas from '@/components/chainsight/MarketGraphCanvas';
import ExplorationTrail from '@/components/chainsight/ExplorationTrail';
import RelationCardPanel from '@/components/chainsight/RelationCardPanel';
import ChainStoryFeed from '@/components/chainsight/ChainStoryFeed';

function MarketGraphPageInner() {
  const params = useSearchParams();
  const focusSymbol = params.get('focus');

  const { data: seedData, isLoading } = useSeedData();
  const state = useExplorationStore();

  // ?focus=SYM 처리: 시드 여부와 무관하게 PG ego 직행(⑳-E — 시드 게이트 해제).
  // 시드면 sector 브레드크럼 포함, 비시드면 sector 미상(null)으로 종목만 초점.
  useEffect(() => {
    if (!focusSymbol) return;
    const sym = focusSymbol.toUpperCase();
    const seedSector = seedData?.seeds.find((s) => s.symbol === sym)?.sector ?? null;
    state.initializeFocusExploration(seedSector, sym);
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

  const hasSeeds = (seedData?.sector_summary?.length ?? 0) > 0;

  if (!hasSeeds) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16">
        <div className="flex flex-col items-center justify-center gap-3 text-center">
          <div className="h-10 w-10 rounded-full border-2 border-blue-400/60 border-t-transparent animate-spin" />
          <p className="text-gray-800 dark:text-gray-200 text-base font-medium">
            오늘의 시드 데이터를 준비하고 있어요
          </p>
          <p className="text-gray-500 dark:text-gray-400 text-sm max-w-md">
            시장 종료 후 자동으로 선정됩니다. 잠시 후 자동으로 갱신돼요.
            계속 이 화면이면 잠시 뒤 새로고침해 주세요.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-4 space-y-4">
      {/* ① 섹터 바 */}
      <SectorBar sectors={seedData?.sector_summary || []} />

      {/* ② 관계 칩 바 — § 5-1: SectorBar와 MarketGraphCanvas 사이, 섹터 미선택 시 disabled */}
      <RelationFilterChips disabled={!state.selectedSector} />

      {/* ③ 그래프 캔버스 */}
      <MarketGraphCanvas />

      {/* ④ 탐색 트레일 */}
      <ExplorationTrail />

      {/* ⑤ 관계 카드 패널 */}
      <RelationCardPanel />

      {/* ⑥ 체인 스토리 피드 */}
      <ChainStoryFeed />
    </div>
  );
}

export default function MarketGraphPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="flex items-center justify-center h-[200px]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          </div>
        </div>
      }
    >
      <MarketGraphPageInner />
    </Suspense>
  );
}
