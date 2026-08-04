'use client';

import { useMemo, useState } from 'react';
import { useExplorationStore } from '@/lib/stores/explorationStore';
import { useEgo } from '@/hooks/useMarketView';
import GraphStatePanel from './GraphStatePanel';
import { egoToMindmap } from './egoMindmap';
import type { MindmapBranch, MindmapLeaf, MindmapSubgroup } from './egoMindmap';

/**
 * 마인드맵 뷰 (맵-3) — ⑳-3 S3-MINDMAP S5.
 *
 * 접힘 카테고리(2층: 상위 가지 + 하위 그룹) + 클릭 펼침(leaf cap 12). SEC 근거 가지와
 * 시장 파생 가지를 시각 구분. leaf 클릭 = selectNode(카드 리스트 필터 연동).
 * PRICE_CORRELATED 제외 건수는 하단에 투명화 표기.
 */

const LEAF_CAP = 12; // 한 그룹 펼침 시 최초 노출 상한

export default function MindmapView() {
  const { centerSymbol, selectNode } = useExplorationStore();
  const { data, isLoading, isError, refetch } = useEgo(centerSymbol);
  const mindmap = useMemo(() => (data ? egoToMindmap(data) : null), [data]);

  if (!centerSymbol) return null;
  if (isError) {
    return <GraphStatePanel variant="load-error" symbol={centerSymbol} onRetry={() => refetch()} />;
  }
  if (isLoading || !data || !mindmap) {
    return (
      <div className="flex flex-col items-center justify-center h-[560px] gap-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
        <p className="text-sm text-gray-400">마인드맵을 구성하는 중...</p>
      </div>
    );
  }
  if (mindmap.branches.length === 0) {
    return <GraphStatePanel variant="empty-neighbors" symbol={centerSymbol} />;
  }

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      <div className="flex items-baseline gap-2 mb-3">
        <span className="font-semibold text-base">{mindmap.center.symbol}</span>
        <span className="text-xs text-gray-500 truncate max-w-[240px]">{mindmap.center.name}</span>
        <span className="text-[11px] text-gray-400">· {mindmap.branches.length}개 카테고리</span>
      </div>

      <div className="flex flex-col gap-1.5">
        {mindmap.branches.map((br) => (
          <Branch key={br.key} branch={br} onSelect={selectNode} />
        ))}
      </div>

      {mindmap.excludedPriceCorrelated > 0 && (
        <p className="mt-3 text-[11px] text-gray-400">
          주가 동조(PRICE_CORRELATED) {mindmap.excludedPriceCorrelated}건은 Peer 중복이라 마인드맵에서 제외.
        </p>
      )}
    </div>
  );
}

/** 상위 가지 — SEC/시장 시각 구분, 접힘/펼침. */
function Branch({
  branch,
  onSelect,
}: {
  branch: MindmapBranch;
  onSelect: (symbol: string, relationType: string) => void;
}) {
  const [open, setOpen] = useState(false);
  // SEC 근거 = 진한 테두리(파랑), 시장 파생 = 회색
  const accent = branch.isSec
    ? 'border-blue-300 dark:border-blue-700'
    : 'border-gray-200 dark:border-gray-700';
  const dot = branch.isSec ? 'bg-blue-500' : 'bg-gray-400';

  return (
    <div className={`rounded-lg border ${accent}`}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left"
        aria-expanded={open}
      >
        <span className={`w-2 h-2 rounded-full ${dot}`} aria-hidden />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{branch.label}</span>
        <span className="text-[11px] text-gray-400 tabular-nums" aria-label={`${branch.count}건`}>
          {branch.count}
        </span>
        {branch.isSec && (
          <span className="text-[10px] text-blue-500 border border-blue-300 rounded px-1">SEC</span>
        )}
        <span className="ml-auto text-gray-400 text-xs">{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="px-3 pb-2">
          {branch.subgroups.length > 0
            ? branch.subgroups.map((sg) => (
                <Subgroup key={sg.key} subgroup={sg} onSelect={onSelect} />
              ))
            : <LeafList leaves={branch.leaves} onSelect={onSelect} />}
        </div>
      )}
    </div>
  );
}

/** 하위 그룹(L2 industry) — 접힘/펼침. */
function Subgroup({
  subgroup,
  onSelect,
}: {
  subgroup: MindmapSubgroup;
  onSelect: (symbol: string, relationType: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1.5 ml-2 border-l border-gray-200 dark:border-gray-700 pl-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 py-1 text-left"
        aria-expanded={open}
      >
        <span className="text-xs text-gray-600 dark:text-gray-300">{subgroup.label}</span>
        <span className="text-[11px] text-gray-400 tabular-nums">{subgroup.count}</span>
        <span className="ml-auto text-gray-400 text-xs">{open ? '▾' : '▸'}</span>
      </button>
      {open && <LeafList leaves={subgroup.leaves} onSelect={onSelect} />}
    </div>
  );
}

/** leaf 목록 — cap 12, 더보기, 클릭 시 카드 리스트로 연동. */
function LeafList({
  leaves,
  onSelect,
}: {
  leaves: MindmapLeaf[];
  onSelect: (symbol: string, relationType: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? leaves : leaves.slice(0, LEAF_CAP);
  return (
    <div className="flex flex-wrap gap-1.5 py-1">
      {shown.map((leaf) => (
        <button
          key={`${leaf.symbol}-${leaf.relation_type}`}
          onClick={() => onSelect(leaf.symbol, leaf.relation_type)}
          className="px-2 py-0.5 text-[11px] rounded-full border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 hover:border-blue-400 transition"
          title={`${leaf.name} · ${leaf.relation_type}`}
          aria-label={`${leaf.symbol} — 카드에서 탐색`}
        >
          {leaf.symbol}
        </button>
      ))}
      {leaves.length > LEAF_CAP && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="px-2 py-0.5 text-[11px] text-blue-600 dark:text-blue-400"
        >
          +{leaves.length - LEAF_CAP} 더보기
        </button>
      )}
    </div>
  );
}
