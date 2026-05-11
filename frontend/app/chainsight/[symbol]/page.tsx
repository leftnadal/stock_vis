'use client';

/**
 * Chain Sight 전용 워크스페이스
 *
 * /chainsight/[symbol]
 * 3-panel: 좌측 AI Guide | 중앙 그래프 | 우측 노드 상세
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import Link from 'next/link';

import { useGraphData, useSuggestions, useTrace } from '@/hooks/useChainsight';
import type { GraphNode, SuggestionCategory } from '@/types/chainsight';

import AIGuidePanel from '@/components/chainsight/AIGuidePanel';
import NodeDetailPanel from '@/components/chainsight/NodeDetailPanel';
import RelationLegend from '@/components/chainsight/RelationLegend';
import TracePathView from '@/components/chainsight/TracePathView';
import FilterPanel, { type FilterState } from '@/components/chainsight/FilterPanel';
import MobileCardList from '@/components/chainsight/MobileCardList';

// react-force-graph-2d: SSR 불가 → dynamic import
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

// GraphCanvas도 dynamic (ForceGraph2D 의존)
const GraphCanvas = dynamic(
  () => import('@/components/chainsight/GraphCanvas'),
  { ssr: false }
);

// 카테고리 ID → 관계 타입 매핑
const CATEGORY_REL_MAP: Record<string, string[]> = {
  peers: ['PEER_OF'],
  same_industry: ['BELONGS_TO_INDUSTRY'],
  co_mentioned: ['CO_MENTIONED', 'RELATED_TO'],
  same_sector: ['BELONGS_TO_SECTOR'],
};

export default function ChainSightPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = (params.symbol as string || '').toUpperCase();

  const [depth, setDepth] = useState(1);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [traceTarget, setTraceTarget] = useState<{ from: string; to: string } | null>(null);
  const [leftOpen, setLeftOpen] = useState(true);
  const [filterOpen, setFilterOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [graphOverlay, setGraphOverlay] = useState(false);
  const [filters, setFilters] = useState<FilterState>({
    relTypes: new Set([
      'PEER_OF', 'SUPPLIES_TO', 'CUSTOMER_OF', 'COMPETES_WITH',
      'CO_MENTIONED', 'HAS_THEME', 'BELONGS_TO_SECTOR', 'BELONGS_TO_INDUSTRY', 'RELATED_TO',
    ]),
    depth: 1,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const [canvasSize, setCanvasSize] = useState({ w: 800, h: 600 });

  // ── API 데이터 ──
  const { data: graphData, isLoading: graphLoading } = useGraphData(symbol, depth);
  const { data: suggestions, isLoading: sugLoading } = useSuggestions(symbol);
  const { data: traceData, isLoading: traceLoading } = useTrace(
    traceTarget?.from || '', traceTarget?.to || ''
  );

  // ── 관계 필터 (카테고리 선택 또는 프로 필터) ──
  const highlightRelTypes = useMemo(() => {
    if (activeCategory) {
      return CATEGORY_REL_MAP[activeCategory] || [];
    }
    // 프로 필터: 전부 선택되면 빈 배열(=필터 없음), 일부만 선택되면 해당 타입만
    const allTypes = [
      'PEER_OF', 'SUPPLIES_TO', 'CUSTOMER_OF', 'COMPETES_WITH',
      'CO_MENTIONED', 'HAS_THEME', 'BELONGS_TO_SECTOR', 'BELONGS_TO_INDUSTRY', 'RELATED_TO',
    ];
    if (filters.relTypes.size >= allTypes.length) return [];
    return Array.from(filters.relTypes);
  }, [activeCategory, filters.relTypes]);

  // 필터 변경 핸들러
  const handleFiltersChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    if (newFilters.depth !== depth) {
      setDepth(newFilters.depth);
    }
  }, [depth]);

  // ── 선택된 노드 정보 ──
  const selectedNodeData = useMemo<GraphNode | null>(() => {
    if (!selectedNode || !graphData) return null;
    if (graphData.center.ticker === selectedNode) return graphData.center;
    return graphData.nodes.find(n => n.ticker === selectedNode) || null;
  }, [selectedNode, graphData]);

  // ── 선택된 노드의 관계 라벨 ──
  const selectedRelLabel = useMemo(() => {
    if (!selectedNode || !graphData) return '';
    const edge = graphData.edges.find(
      e => e.from === selectedNode || e.to === selectedNode
    );
    if (!edge) return '';
    const { getRelationStyle } = require('@/components/chainsight/graphStyles');
    const style = getRelationStyle(edge.derived_type || edge.type);
    return style.label;
  }, [selectedNode, graphData]);

  // ── 캔버스 크기 + 모바일 감지 ──
  useEffect(() => {
    function updateSize() {
      setIsMobile(window.innerWidth < 768);
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setCanvasSize({ w: rect.width, h: rect.height });
      }
    }
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, [leftOpen]);

  // ── 핸들러 ──
  const handleNodeClick = useCallback((ticker: string) => {
    setSelectedNode(prev => prev === ticker ? null : ticker);
  }, []);

  const handleExploreHere = useCallback((ticker: string) => {
    router.push(`/chainsight/${ticker}`);
  }, [router]);

  const handleStartTrace = useCallback((to: string) => {
    setTraceTarget({ from: symbol, to });
  }, [symbol]);

  const handleCategorySelect = useCallback((catId: string | null) => {
    setActiveCategory(catId);
  }, []);

  const handleTrace = useCallback((from: string, to: string) => {
    setTraceTarget({ from, to });
  }, []);

  if (!symbol) return null;

  // ── 모바일: 카드 리스트 기본 + 그래프 오버레이 ──
  if (isMobile && !graphOverlay) {
    return (
      <div className="h-screen flex flex-col bg-gray-50">
        <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-3">
            <Link href={`/stocks/${symbol}`} className="text-gray-500 hover:text-gray-800">←</Link>
            <h1 className="text-lg font-bold">{symbol}</h1>
            <span className="text-sm text-gray-500">Chain Sight</span>
          </div>
        </header>
        <MobileCardList
          graphData={graphData}
          suggestions={suggestions}
          symbol={symbol}
          onShowGraph={() => setGraphOverlay(true)}
        />
      </div>
    );
  }

  // ── 모바일 그래프 오버레이 ──
  if (isMobile && graphOverlay) {
    return (
      <div className="fixed inset-0 z-50 bg-white flex flex-col">
        <header className="h-12 bg-white border-b border-gray-200 flex items-center justify-between px-4 shrink-0">
          <span className="text-sm font-bold">{symbol} 그래프</span>
          <button
            onClick={() => setGraphOverlay(false)}
            className="px-3 py-1 text-sm border border-gray-200 rounded-lg"
          >
            닫기
          </button>
        </header>
        <div ref={containerRef} className="flex-1">
          {graphData && (
            <GraphCanvas
              data={graphData}
              width={canvasSize.w || window.innerWidth}
              height={(canvasSize.h || window.innerHeight) - 48}
              selectedNode={selectedNode}
              highlightRelTypes={[]}
              onNodeClick={handleNodeClick}
              ForceGraph2D={ForceGraph2D as unknown as React.ComponentType<Record<string, unknown>>}
            />
          )}
        </div>
        {/* 모바일 노드 상세 바텀 시트 */}
        {selectedNodeData && (
          <div className="bg-white border-t border-gray-200 p-3 max-h-48 overflow-y-auto">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-bold">{selectedNodeData.ticker}</span>
                <span className="text-xs text-gray-500 ml-2">{selectedNodeData.name}</span>
              </div>
              <button onClick={() => setSelectedNode(null)} className="text-gray-400 text-sm">✕</button>
            </div>
            <div className="flex gap-2 mt-2">
              <Link
                href={`/chainsight/${selectedNodeData.ticker}`}
                className="flex-1 text-center text-xs py-2 rounded-lg bg-gray-800 text-white"
              >
                탐색
              </Link>
              <Link
                href={`/thesis/new?symbol=${selectedNodeData.ticker}&from=${symbol}`}
                className="flex-1 text-center text-xs py-2 rounded-lg bg-blue-600 text-white"
              >
                가설
              </Link>
              <Link
                href={`/stocks/${selectedNodeData.ticker}?tab=validation`}
                className="flex-1 text-center text-xs py-2 rounded-lg bg-gray-100 text-gray-700"
              >
                검증
              </Link>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── 데스크톱: 3-panel 레이아웃 ──
  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 헤더 */}
      <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          <Link href={`/stocks/${symbol}`} className="text-gray-500 hover:text-gray-800">
            ←
          </Link>
          <h1 className="text-lg font-bold">{symbol}</h1>
          <span className="text-sm text-gray-500">Chain Sight</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Depth 전환 */}
          <div className="flex border border-gray-200 rounded-lg overflow-hidden text-sm">
            {[1, 2, 3].map(d => (
              <button
                key={d}
                onClick={() => setDepth(d)}
                className={`px-3 py-1.5 ${
                  depth === d
                    ? 'bg-gray-800 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                {d}
              </button>
            ))}
          </div>

          {/* 필터 */}
          <button
            onClick={() => setFilterOpen(!filterOpen)}
            className={`px-3 py-1.5 text-sm border rounded-lg ${
              filterOpen ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 hover:bg-gray-50'
            }`}
          >
            필터
          </button>

          {/* 좌측 패널 토글 */}
          <button
            onClick={() => setLeftOpen(!leftOpen)}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            {leftOpen ? '패널 닫기' : 'AI 가이드'}
          </button>
        </div>

        {/* 필터 패널 (절대 위치) */}
        {filterOpen && (
          <FilterPanel
            filters={filters}
            onFiltersChange={handleFiltersChange}
            onClose={() => setFilterOpen(false)}
          />
        )}
      </header>

      {/* 메인 3-panel */}
      <div className="flex-1 flex overflow-hidden">
        {/* 좌측: AI Guide */}
        {leftOpen && (
          <aside className="w-60 border-r border-gray-200 bg-white shrink-0 overflow-hidden">
            <AIGuidePanel
              categories={suggestions?.categories || []}
              isLoading={sugLoading}
              activeCategory={activeCategory}
              centerSymbol={symbol}
              onCategorySelect={handleCategorySelect}
              onTrace={handleTrace}
            />
          </aside>
        )}

        {/* 중앙: 그래프 */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* Trace 결과 (그래프 상단) */}
          {traceTarget && (
            <div className="p-3 border-b border-gray-200 bg-white">
              <TracePathView
                trace={traceData || null}
                isLoading={traceLoading}
                onClose={() => setTraceTarget(null)}
              />
            </div>
          )}

          {/* 그래프 캔버스 */}
          <div ref={containerRef} className="flex-1 relative">
            {graphLoading ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-sm text-gray-400">그래프 로딩 중...</div>
              </div>
            ) : graphData ? (
              <GraphCanvas
                data={graphData}
                width={canvasSize.w}
                height={canvasSize.h}
                selectedNode={selectedNode}
                highlightRelTypes={highlightRelTypes}
                onNodeClick={handleNodeClick}
                ForceGraph2D={ForceGraph2D as unknown as React.ComponentType<Record<string, unknown>>}
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-sm text-gray-400">데이터가 없습니다.</div>
              </div>
            )}
          </div>

          {/* 하단 범례 + 메타 */}
          <div className="h-10 bg-white border-t border-gray-200 flex items-center justify-between px-4">
            <RelationLegend />
            {graphData && (
              <span className="text-xs text-gray-400">
                노드 {graphData.meta.node_count} | 엣지 {graphData.meta.edge_count} | {graphData.meta.query_ms}ms
              </span>
            )}
          </div>
        </main>

        {/* 우측: 노드 상세 */}
        <aside className="w-72 border-l border-gray-200 bg-white shrink-0 overflow-y-auto hidden lg:block">
          <NodeDetailPanel
            node={selectedNodeData}
            centerSymbol={symbol}
            relationLabel={selectedRelLabel}
            onExploreHere={handleExploreHere}
            onStartTrace={handleStartTrace}
          />
        </aside>
      </div>
    </div>
  );
}
