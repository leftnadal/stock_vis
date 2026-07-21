'use client';

import { useExplorationStore } from '@/lib/stores/explorationStore';
import { useSeedData } from '@/hooks/useMarketView';
import type { SeedNode } from '@/types/chainsight';
import { CHANGE_TEXT } from '@/components/common/colorSemantics';

const REASON_LABELS: Record<string, string> = {
  price_top5: '수익률 상위 이상치',
  price_bottom5: '수익률 하위 이상치',
  volume_surge: '거래량 급증',
  sector_outlier: '섹터 이상치',
  relation_upgrade: '관계 상향',
  relation_downgrade: '관계 하향',
  relation_new: '신규 관계 발견',
  comention_surge: '동시출현 급증',
};

/**
 * 섹터 프리-포커스 시드 카드 패널.
 *
 * ⑳-2: ego 모드(centerSymbol 존재)의 관계 카드는 EgoDrilldown(RelationCardList,
 * PG 네이티브 ego)이 담당한다. 여기서는 중복/구 Neo4j(useNeighbors) 브랜치를 제거하고
 * 섹터 프리-포커스 시드 카드만 유지한다.
 */
export default function RelationCardPanel() {
  const { selectedSector, centerSymbol } = useExplorationStore();
  const { data: seedData } = useSeedData();

  // ego 모드는 EgoDrilldown이 담당 → 여기선 미표시(중복 방지).
  if (centerSymbol) return null;

  // empty state
  if (!selectedSector) {
    return (
      <div className="py-8 text-center text-gray-400 dark:text-gray-500 text-sm">
        섹터를 선택하면 대표 시드 카드가 표시됩니다
      </div>
    );
  }

  // pre-focus: 섹터 시드 카드
  const sectorSeeds = (seedData?.seeds || []).filter((s) => s.sector === selectedSector);
  return <SeedCardList seeds={sectorSeeds} />;
}

// ── Pre-focus: 시드 카드 목록 ──

function SeedCardList({ seeds }: { seeds: SeedNode[] }) {
  const { selectNode } = useExplorationStore();

  if (!seeds.length) {
    return (
      <div className="py-6 text-center text-gray-400 text-sm">
        이 섹터에 시드 노드가 없습니다
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 py-3">
      {seeds.map((seed) => (
        <div
          key={seed.symbol}
          className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
        >
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className="font-semibold text-sm">{seed.symbol}</span>
              <span className="text-xs text-gray-500 ml-2">{seed.name}</span>
            </div>
            <SeedBadge type={seed.seed_type} />
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            {seed.seed_reasons.map((r) => REASON_LABELS[r] || r).join(', ')}
          </p>

          <div className="flex items-center gap-3 text-xs mb-3">
            <span className={seed.daily_return >= 0 ? CHANGE_TEXT.up : CHANGE_TEXT.down}>
              {seed.daily_return > 0 ? '+' : ''}{seed.daily_return}%
            </span>
            {seed.volume_ratio > 1 && (
              <span className="text-gray-500">Vol {seed.volume_ratio.toFixed(1)}x</span>
            )}
          </div>

          <button
            onClick={() => selectNode(seed.symbol)}
            className="w-full py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded hover:bg-blue-100 dark:hover:bg-blue-900/40 transition"
          >
            여기서 탐색
          </button>
        </div>
      ))}
    </div>
  );
}

function SeedBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    price: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    volume: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    relation: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    comention: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  };
  return (
    <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${colors[type] || colors.price}`}>
      {type}
    </span>
  );
}
