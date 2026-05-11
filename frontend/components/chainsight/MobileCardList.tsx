'use client';

/**
 * 모바일용 카드 리스트
 *
 * 카테고리 탭 + 종목 카드 리스트 (그래프 대신 기본 뷰)
 */

import Link from 'next/link';
import { useState, useMemo } from 'react';
import type { GraphResponse, SuggestionsResponse, GraphNode } from '@/types/chainsight';
import { getRelationStyle, getSectorColor } from './graphStyles';

interface MobileCardListProps {
  graphData: GraphResponse | undefined;
  suggestions: SuggestionsResponse | undefined;
  symbol: string;
  onShowGraph: () => void;
}

export default function MobileCardList({
  graphData,
  suggestions,
  symbol,
  onShowGraph,
}: MobileCardListProps) {
  const [activeTab, setActiveTab] = useState<string>('all');

  const categories = suggestions?.categories || [];

  // 노드를 카테고리별로 분류
  const categorizedNodes = useMemo(() => {
    if (!graphData) return {};

    const result: Record<string, GraphNode[]> = { all: [] };

    // 모든 Stock 노드 (center 제외)
    const nodes = graphData.nodes.filter(n => n.ticker && n.ticker !== symbol);
    result.all = nodes;

    // 엣지 기반 분류
    for (const edge of graphData.edges) {
      const relType = edge.derived_type || edge.type;
      const otherTicker = edge.from === symbol ? edge.to : edge.from;
      const node = nodes.find(n => n.ticker === otherTicker);
      if (!node) continue;

      if (!result[relType]) result[relType] = [];
      result[relType].push(node);
    }

    return result;
  }, [graphData, symbol]);

  // 탭별 표시할 노드
  const displayNodes = useMemo(() => {
    if (activeTab === 'all') return categorizedNodes.all || [];

    // 카테고리 ID → rel_type 매핑
    const catRelMap: Record<string, string[]> = {
      peers: ['PEER_OF'],
      same_industry: ['BELONGS_TO_INDUSTRY'],
      co_mentioned: ['CO_MENTIONED', 'RELATED_TO'],
      same_sector: ['BELONGS_TO_SECTOR'],
    };

    const relTypes = catRelMap[activeTab] || [activeTab];
    const seen = new Set<string>();
    const nodes: GraphNode[] = [];
    for (const rt of relTypes) {
      for (const n of categorizedNodes[rt] || []) {
        if (!seen.has(n.ticker)) {
          seen.add(n.ticker);
          nodes.push(n);
        }
      }
    }
    return nodes;
  }, [activeTab, categorizedNodes]);

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* 카테고리 탭 바 */}
      <div className="bg-white border-b border-gray-200 px-4 py-2 overflow-x-auto">
        <div className="flex gap-2 min-w-max">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 text-sm rounded-full whitespace-nowrap ${
              activeTab === 'all'
                ? 'bg-gray-800 text-white'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            전체 {categorizedNodes.all?.length || 0}
          </button>
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => setActiveTab(cat.id)}
              className={`px-3 py-1.5 text-sm rounded-full whitespace-nowrap ${
                activeTab === cat.id
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              {cat.label} {cat.count}
            </button>
          ))}
        </div>
      </div>

      {/* 카드 리스트 */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {displayNodes.length === 0 ? (
          <div className="text-center py-12 text-sm text-gray-400">
            해당 카테고리에 종목이 없습니다.
          </div>
        ) : (
          displayNodes.map(node => (
            <div
              key={node.ticker}
              className="bg-white rounded-xl border border-gray-200 p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-white text-xs font-bold"
                    style={{ backgroundColor: getSectorColor(node.sector || '') }}
                  >
                    {node.ticker.slice(0, 3)}
                  </div>
                  <div>
                    <Link
                      href={`/stocks/${node.ticker}`}
                      className="font-semibold text-sm hover:text-blue-600"
                    >
                      {node.ticker}
                    </Link>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {node.name || node.ticker}
                    </p>
                  </div>
                </div>
              </div>

              {/* 프로파일 태그 */}
              <div className="flex flex-wrap gap-1.5 mt-3">
                {node.sector && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                    {node.sector}
                  </span>
                )}
                {node.growth_stage && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">
                    {node.growth_stage}
                  </span>
                )}
                {node.capital_dna && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-50 text-green-700">
                    {node.capital_dna}
                  </span>
                )}
              </div>

              {/* CTA */}
              <div className="flex gap-2 mt-3">
                <Link
                  href={`/thesis/new?symbol=${node.ticker}&from=${symbol}`}
                  className="flex-1 text-center text-xs py-1.5 rounded-lg bg-blue-600 text-white"
                >
                  가설 생성
                </Link>
                <Link
                  href={`/chainsight/${node.ticker}`}
                  className="flex-1 text-center text-xs py-1.5 rounded-lg bg-gray-100 text-gray-700"
                >
                  탐색
                </Link>
                <Link
                  href={`/stocks/${node.ticker}?tab=validation`}
                  className="flex-1 text-center text-xs py-1.5 rounded-lg bg-gray-100 text-gray-700"
                >
                  검증
                </Link>
              </div>
            </div>
          ))
        )}
      </div>

      {/* 그래프 보기 FAB */}
      <div className="p-4 bg-white border-t border-gray-200">
        <button
          onClick={onShowGraph}
          className="w-full py-3 text-sm font-medium rounded-xl bg-gray-800 text-white"
        >
          그래프로 보기
        </button>
      </div>
    </div>
  );
}
