'use client';

import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useExplorationStore } from '@/lib/stores/explorationStore';
import { useNeighbors, useSeedData } from '@/hooks/useMarketView';
import type { Neighbor, SeedNode } from '@/types/chainsight';
import { CHANGE_TEXT } from './colorSemantics';

const RELATION_TEMPLATES: Record<string, string> = {
  SUPPLIES_TO: '공급망 상류/하류 연결',
  CUSTOMER_OF: '공급망 상류/하류 연결',
  COMPETES_WITH: '직접 경쟁 관계',
  PEER_OF: '동종 비교 대상',
  CO_MENTIONED: '최근 시장/뉴스에서 동시 해석',
  PRICE_CORRELATED: '가격 움직임 유사',
  RELATED_TO: '관련 종목',
  HAS_THEME: '그룹 공유',
  HELD_BY_SAME_FUND: '동일 펀드 보유',
};

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

const RELATION_GROUPS = [
  { key: 'supply_chain', label: 'Supply Chain', types: ['SUPPLIES_TO', 'CUSTOMER_OF'] },
  { key: 'competitors', label: 'Competitors', types: ['COMPETES_WITH'] },
  { key: 'peers', label: 'Peers', types: ['PEER_OF'] },
  { key: 'co_mentioned', label: 'Co-mentioned', types: ['CO_MENTIONED', 'PRICE_CORRELATED'] },
  { key: 'related', label: 'Related', types: ['RELATED_TO', 'HAS_THEME', 'HELD_BY_SAME_FUND'] },
];

function buildWhyNow(neighbor: Neighbor): string {
  if (neighbor.seed_reasons?.length > 0) {
    return neighbor.seed_reasons.map((r) => REASON_LABELS[r] || r).join(', ');
  }
  if (Math.abs(neighbor.daily_return) > 3) {
    return `수익률 ${neighbor.daily_return > 0 ? '+' : ''}${neighbor.daily_return}%`;
  }
  if (neighbor.volume_ratio > 2) {
    return `거래량 ${neighbor.volume_ratio.toFixed(1)}배`;
  }
  return '관계 기반 탐색 후보';
}

export default function RelationCardPanel() {
  const { selectedSector, centerSymbol, selectNode } = useExplorationStore();
  const { data: seedData } = useSeedData();
  const { data: neighborData, isLoading, isError } = useNeighbors(centerSymbol);

  // empty state
  if (!selectedSector && !centerSymbol) {
    return (
      <div className="py-8 text-center text-gray-400 dark:text-gray-500 text-sm">
        섹터를 선택하면 대표 시드 카드가 표시됩니다
      </div>
    );
  }

  // pre-focus: 섹터 시드 카드
  if (selectedSector && !centerSymbol) {
    const sectorSeeds = (seedData?.seeds || []).filter(
      (s) => s.sector === selectedSector,
    );
    return <SeedCardList seeds={sectorSeeds} />;
  }

  // loading state
  if (centerSymbol && isLoading) {
    return (
      <div className="py-8 text-center text-gray-400 dark:text-gray-500 text-sm">
        <div className="inline-block w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin mb-2" />
        <p>관계 데이터를 불러오는 중...</p>
      </div>
    );
  }

  // error state
  if (centerSymbol && isError) {
    return (
      <div className="py-8 text-center text-sm">
        <p className="text-red-500 dark:text-red-400 mb-2">관계 데이터를 불러오지 못했습니다</p>
        <p className="text-gray-400 text-xs">네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요</p>
      </div>
    );
  }

  // focused: 관계 카드
  if (centerSymbol && neighborData) {
    return <RelationCardGroups neighbors={neighborData.neighbors} />;
  }

  return null;
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

// ── Focused: 관계 카드 그룹 ──

function RelationCardGroups({ neighbors }: { neighbors: Neighbor[] }) {
  const grouped = useMemo(() => {
    const map = new Map<string, Neighbor[]>();
    for (const group of RELATION_GROUPS) {
      const items = neighbors.filter((n) =>
        group.types.includes(n.relation.display_type),
      );
      if (items.length > 0) {
        map.set(group.key, items);
      }
    }
    return map;
  }, [neighbors]);

  if (grouped.size === 0) {
    return (
      <div className="py-6 text-center text-gray-400 text-sm">
        관계 데이터가 없습니다
      </div>
    );
  }

  return (
    <div className="space-y-4 py-3">
      {RELATION_GROUPS.map((group) => {
        const items = grouped.get(group.key);
        if (!items) return null;
        return (
          <div key={group.key}>
            <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">
              {group.label} ({items.length})
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {items.map((nb) => (
                <RelationCard key={nb.symbol} neighbor={nb} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── 관계 카드 1장 ──

function RelationCard({ neighbor }: { neighbor: Neighbor }) {
  const router = useRouter();
  const { selectNode } = useExplorationStore();
  const confidence = neighbor.relation.truth_score ?? neighbor.relation.market_score ?? 0;

  return (
    <div className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      {/* 상단 */}
      <div className="flex items-center justify-between mb-1.5">
        <div>
          <span className="font-semibold text-sm">{neighbor.symbol}</span>
          <span className="text-xs text-gray-500 ml-1.5">{neighbor.name}</span>
        </div>
        <DisplayTypeBadge type={neighbor.relation.display_type} />
      </div>

      {/* 관계 설명 */}
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
        {RELATION_TEMPLATES[neighbor.relation.display_type] || '관계'}
      </p>

      {/* 시그널 */}
      <p className="text-xs text-gray-600 dark:text-gray-300 mb-2">
        {buildWhyNow(neighbor)}
      </p>

      {/* 메타 */}
      <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
        <span>신뢰도 {confidence}</span>
        <span className={neighbor.daily_return >= 0 ? CHANGE_TEXT.up : CHANGE_TEXT.down}>
          {neighbor.daily_return > 0 ? '+' : ''}{neighbor.daily_return}%
        </span>
      </div>

      {/* CTA */}
      <div className="flex gap-1.5">
        <button
          onClick={() => selectNode(neighbor.symbol, neighbor.relation.display_type)}
          className="flex-1 py-1 text-xs font-medium text-blue-600 bg-blue-50 dark:bg-blue-900/20 rounded hover:bg-blue-100 transition"
        >
          여기서 탐색
        </button>
        <button
          onClick={() => router.push(`/thesis/new?symbol=${neighbor.symbol}&from=chainsight`)}
          className="py-1 px-2 text-xs text-gray-500 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 transition"
        >
          가설
        </button>
        <button
          onClick={() => router.push(`/chainsight/${neighbor.symbol}`)}
          className="py-1 px-2 text-xs text-gray-500 bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 transition"
        >
          Deep
        </button>
      </div>
    </div>
  );
}

// ── 배지 컴포넌트 ──

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

function DisplayTypeBadge({ type }: { type: string }) {
  const labels: Record<string, string> = {
    SUPPLIES_TO: 'Supply',
    CUSTOMER_OF: 'Customer',
    COMPETES_WITH: 'Compete',
    PEER_OF: 'Peer',
    CO_MENTIONED: 'Co-mention',
    PRICE_CORRELATED: 'Corr',
  };
  return (
    <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
      {labels[type] || type}
    </span>
  );
}
