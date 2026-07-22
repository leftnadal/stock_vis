'use client';

import { useMemo, useState } from 'react';
import { useExplorationStore } from '@/lib/stores/explorationStore';
import { useEgo } from '@/hooks/useMarketView';
import GraphStatePanel from './GraphStatePanel';
import {
  CARD_LIST,
  gradeBadge,
  buildNodeMap,
  groupEdgesBySection,
} from './cardListConfig';
import type { EgoEdge, EgoNode } from '@/types/chainsight';

/**
 * 관계 카드 리스트 (⑳-2 S2 → ⑳-G 정직화) — ego 드릴다운 기본 뷰.
 *
 * ⑳-F 진단 반영:
 *  - 연속 신뢰도 바 폐지 → 계단 등급 배지(확정/유력/관찰 · 소스 병기).
 *  - 유형별 섹션 분리(공급망/경쟁/Peer/시장) — 이질 점수 한 축 혼합 제거.
 *  - basis_summary 1줄 노출(근거). 뉴스만 "뉴스 근거 N건", 공시는 basis가 근거(0건 오해 차단).
 *  - "확인일"(last_observed_at) — auto_now 저장 시각을 언급일로 오표기하지 않음.
 * 빈/오류 상태는 GraphStatePanel 재사용(⑳-E).
 */
export default function RelationCardList() {
  const { centerSymbol, selectNode } = useExplorationStore();
  const { data, isLoading, isError, refetch } = useEgo(centerSymbol);
  const [visible, setVisible] = useState<number>(CARD_LIST.initialVisible);

  const nodeMap = useMemo(() => buildNodeMap(data?.nodes ?? []), [data]);
  const sections = useMemo(
    () => groupEdgesBySection(data?.edges ?? []),
    [data],
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

  const loaded = data.edges.length; // 로드된 상위 N (limit 절단)
  if (loaded === 0) {
    return <GraphStatePanel variant="empty-neighbors" symbol={centerSymbol} />;
  }

  const total = data.meta.total_edges; // 전체 관계 수(절단 전)
  const shown = Math.min(visible, loaded);

  // 섹션 순서대로 visible 예산을 소진하며 카드 배분(등급/근거수 tie-break 유지).
  let budget = shown;
  const visibleSections = sections
    .map((sec) => {
      const take = sec.edges.slice(0, Math.max(0, budget));
      budget -= take.length;
      return { ...sec, edges: take };
    })
    .filter((sec) => sec.edges.length > 0);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      {/* 헤더: 중심 종목 + 절단 총량 명시 */}
      <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
        <div className="flex items-baseline gap-2">
          <span className="font-semibold text-base">{data.center.symbol}</span>
          <span className="text-xs text-gray-500 truncate max-w-[220px]">{data.center.name}</span>
        </div>
      </div>
      {/* ⑳-V 반영: 절단 총량 명시 */}
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
        전체 {total}개 관계 중 <span className="font-medium">{shown}개</span> 표시
        {loaded < total && ` (상위 ${loaded}개까지 제공)`}
      </p>

      <div className="flex flex-col gap-4">
        {visibleSections.map((sec) => (
          <section key={sec.key}>
            {/* 섹션 헤더: 라벨 · 개수 · 소스 설명 한 줄 */}
            <div className="flex items-baseline gap-2 mb-2">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">{sec.label}</h3>
              <span className="text-[11px] text-gray-400 tabular-nums">{sec.edges.length}</span>
              <span className="text-[11px] text-gray-400 truncate">· {sec.desc}</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {sec.edges.map((edge) => (
                <RelationCard
                  key={edge.target}
                  edge={edge}
                  node={nodeMap[edge.target]}
                  onOpen={() => selectNode(edge.target, edge.relation_type)}
                />
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* 더 보기 (로드된 범위 내) */}
      {shown < loaded && (
        <div className="mt-4 text-center">
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

/** 단일 관계 카드 — 등급 배지 + 근거 요약 + 확인일. */
function RelationCard({
  edge,
  node,
  onOpen,
}: {
  edge: EgoEdge;
  node?: EgoNode;
  onOpen: () => void;
}) {
  const badge = gradeBadge(edge.grade, edge.grade_source);
  // 뉴스 관계만 건수 노출("뉴스 근거 N건"). 공시(SEC)는 basis_summary가 근거이므로
  // 건수 표기 안 함(⑳-F Q2-3: evidence_count=0 → '근거 0건' 오해 차단).
  const showNewsCount = edge.grade_source === 'co_mention';

  return (
    <button
      onClick={onOpen}
      className="text-left p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-400 hover:shadow-sm transition"
      aria-label={`${edge.target} 관계 카드 — 여기서 탐색`}
    >
      {/* 상단: 심볼 + 회사명 + 등급 배지 */}
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="min-w-0">
          <span className="font-semibold text-sm">{edge.target}</span>
          {node?.name && (
            <span className="block text-[11px] text-gray-500 truncate">{node.name}</span>
          )}
        </div>
        <span
          className="shrink-0 px-1.5 py-0.5 text-[10px] font-semibold rounded border"
          style={{ color: badge.color, borderColor: badge.color }}
        >
          {badge.label}
        </span>
      </div>

      {/* 근거 요약 1줄(말줄임, hover 전체) */}
      {edge.basis_summary && (
        <p
          className="text-[11px] text-gray-600 dark:text-gray-300 truncate mb-1"
          title={edge.basis_summary}
        >
          {edge.basis_summary}
        </p>
      )}

      {/* 하단: 근거 건수(뉴스만) + 확인일 */}
      <div className="flex items-center gap-2 text-[11px] text-gray-400">
        {showNewsCount && <span>뉴스 근거 {edge.evidence_count}건</span>}
        {edge.last_observed_at && (
          <span>
            {showNewsCount ? '· ' : ''}확인일 {edge.last_observed_at}
          </span>
        )}
      </div>
    </button>
  );
}
