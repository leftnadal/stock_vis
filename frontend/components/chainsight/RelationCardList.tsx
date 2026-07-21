'use client';

import { useMemo, useState } from 'react';
import { useExplorationStore } from '@/lib/stores/explorationStore';
import { useEgo } from '@/hooks/useMarketView';
import GraphStatePanel from './GraphStatePanel';
import {
  CARD_LIST,
  DEFAULT_SORT,
  relationBadge,
  buildNodeMap,
  sortEdges,
  type CardSortKey,
} from './cardListConfig';

/**
 * 관계 카드 리스트 (⑳-2 S2) — ego 드릴다운 기본 뷰.
 * PG 네이티브 ego API(useEgo) 소비. 신뢰도 내림차순 기본, 절단 총량 명시 + 더 보기.
 * 빈/오류 상태는 GraphStatePanel 재사용(⑳-E).
 */
export default function RelationCardList() {
  const { centerSymbol, selectNode } = useExplorationStore();
  const { data, isLoading, isError, refetch } = useEgo(centerSymbol);
  const [sortKey, setSortKey] = useState<CardSortKey>(DEFAULT_SORT);
  const [visible, setVisible] = useState<number>(CARD_LIST.initialVisible);

  const nodeMap = useMemo(() => buildNodeMap(data?.nodes ?? []), [data]);
  const sorted = useMemo(
    () => sortEdges(data?.edges ?? [], sortKey),
    [data, sortKey],
  );

  if (!centerSymbol) return null;

  if (isError) {
    return (
      <GraphStatePanel variant="load-error" symbol={centerSymbol} onRetry={() => refetch()} />
    );
  }
  if (isLoading || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-[560px] gap-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
        <p className="text-sm text-gray-400">관계를 불러오는 중...</p>
      </div>
    );
  }
  if (sorted.length === 0) {
    return <GraphStatePanel variant="empty-neighbors" symbol={centerSymbol} />;
  }

  const total = data.meta.total_edges; // 전체 관계 수(절단 전)
  const loaded = sorted.length; // 실제 로드된 상위 N (limit 절단)
  const shown = Math.min(visible, loaded);
  const cards = sorted.slice(0, shown);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      {/* 헤더: 중심 종목 + 정렬 + 절단 총량 명시 */}
      <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
        <div className="flex items-baseline gap-2">
          <span className="font-semibold text-base">{data.center.symbol}</span>
          <span className="text-xs text-gray-500 truncate max-w-[180px]">{data.center.name}</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <label className="text-gray-500">정렬</label>
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as CardSortKey)}
            className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1"
          >
            <option value="confidence">신뢰도순</option>
            <option value="recent">최근 언급순</option>
          </select>
        </div>
      </div>

      {/* ⑳-V 반영: 절단 총량 명시 */}
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
        전체 {total}개 관계 중 <span className="font-medium">{shown}개</span> 표시
        {loaded < total && ` (상위 ${loaded}개까지 제공)`}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {cards.map((edge) => {
          const node = nodeMap[edge.target];
          const badge = relationBadge(edge.relation_type);
          const confidence = Math.round(edge.truth_score);
          return (
            <button
              key={edge.target}
              onClick={() => selectNode(edge.target, edge.relation_type)}
              className="text-left p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-400 hover:shadow-sm transition"
              aria-label={`${edge.target} 관계 카드 — 여기서 탐색`}
            >
              {/* 상단: 심볼 + 회사명 + 관계 배지 */}
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="min-w-0">
                  <span className="font-semibold text-sm">{edge.target}</span>
                  {node?.name && (
                    <span className="block text-[11px] text-gray-500 truncate">{node.name}</span>
                  )}
                </div>
                <span
                  className="shrink-0 px-1.5 py-0.5 text-[10px] font-medium rounded text-white"
                  style={{ backgroundColor: badge.color }}
                >
                  {badge.label}
                </span>
              </div>

              {/* 신뢰도 숫자 + 바 */}
              <div className="mb-2">
                <div className="flex items-center justify-between text-[11px] text-gray-500 mb-0.5">
                  <span>신뢰도</span>
                  <span className="font-medium tabular-nums text-gray-700 dark:text-gray-200">{confidence}</span>
                </div>
                <div className="h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                  <div
                    className="h-full bg-blue-500"
                    style={{ width: `${Math.max(0, Math.min(100, confidence))}%` }}
                  />
                </div>
              </div>

              {/* 근거 건수 + 최근 언급일 */}
              <div className="flex items-center gap-2 text-[11px] text-gray-400">
                <span>근거 {edge.evidence_count}건</span>
                {edge.last_mentioned && <span>· {edge.last_mentioned}</span>}
              </div>
            </button>
          );
        })}
      </div>

      {/* 더 보기 (로드된 범위 내) */}
      {shown < loaded && (
        <div className="mt-3 text-center">
          <button
            onClick={() => setVisible((v) => v + CARD_LIST.loadMoreStep)}
            className="px-4 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition"
          >
            더 보기 ({loaded - shown}개)
          </button>
        </div>
      )}
    </div>
  );
}
