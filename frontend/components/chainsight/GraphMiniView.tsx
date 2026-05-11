'use client';

/**
 * 종목 상세 Chain Sight 탭용 미니 그래프
 *
 * 정적 스냅샷 (인터랙션 최소) + 연결 종목 태그 + "전체 탐색" CTA
 */

import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useMemo, useRef, useEffect, useState } from 'react';

import { useGraphData, useSuggestions } from '@/hooks/useChainsight';
import { getRelationStyle, getSectorColor, getNodeRadius } from './graphStyles';
import type { ForceNode } from '@/types/chainsight';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

interface GraphMiniViewProps {
  symbol: string;
}

export default function GraphMiniView({ symbol }: GraphMiniViewProps) {
  const { data: graphData, isLoading } = useGraphData(symbol, 1);
  const { data: suggestions } = useSuggestions(symbol);
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);

  useEffect(() => {
    if (containerRef.current) {
      setWidth(containerRef.current.offsetWidth);
    }
  }, []);

  const graphFormatted = useMemo(() => {
    if (!graphData?.center) return { nodes: [], links: [] };

    const nodes: ForceNode[] = [{
      id: graphData.center.ticker,
      ticker: graphData.center.ticker,
      name: graphData.center.name || graphData.center.ticker,
      sector: graphData.center.sector || '',
      market_cap: 0,
      pagerank: 1,
      isCenter: true,
      depth: 0,
    }];

    for (const n of graphData.nodes) {
      if (n.ticker && n.ticker !== graphData.center.ticker) {
        nodes.push({
          id: n.ticker,
          ticker: n.ticker,
          name: n.name || n.ticker,
          sector: n.sector || '',
          market_cap: 0,
          pagerank: n.pagerank_score || 0.5,
          isCenter: false,
          depth: 1,
        });
      }
    }

    const links = graphData.edges
      .filter(e => nodes.some(n => n.id === e.from) && nodes.some(n => n.id === e.to))
      .map(e => ({
        source: e.from,
        target: e.to,
        color: getRelationStyle(e.derived_type || e.type).color,
      }));

    return { nodes, links };
  }, [graphData]);

  // 연결 종목 태그
  const connectedTags = useMemo(() => {
    if (!suggestions?.categories) return [];
    const tags: { ticker: string; label: string }[] = [];
    for (const cat of suggestions.categories) {
      for (const t of cat.top_tickers.slice(0, 2)) {
        tags.push({ ticker: t, label: cat.label });
      }
    }
    return tags.slice(0, 6);
  }, [suggestions]);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4 py-8">
        <div className="h-64 bg-gray-100 rounded-lg" />
        <div className="h-8 bg-gray-100 rounded w-1/2" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold">Chain Sight 관계 탐색</h3>
        <Link
          href={`/chainsight/${symbol}`}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
        >
          전체 탐색 →
        </Link>
      </div>

      {/* 미니 그래프 */}
      <div ref={containerRef} className="bg-gray-50 rounded-lg overflow-hidden" style={{ height: 360 }}>
        {graphFormatted.nodes.length > 0 ? (
          /* @ts-expect-error react-force-graph-2d의 타입이 Canvas 콜백을 완전히 지원하지 않음 */
          <ForceGraph2D
            width={width}
            height={360}
            graphData={graphFormatted}
            nodeId="id"
            nodeCanvasObject={(node: ForceNode, ctx: CanvasRenderingContext2D) => {
              const r = getNodeRadius(node.isCenter, node.pagerank);
              const x = (node as unknown as { x: number }).x;
              const y = (node as unknown as { y: number }).y;

              ctx.beginPath();
              ctx.arc(x, y, r, 0, Math.PI * 2);
              ctx.fillStyle = getSectorColor(node.sector);
              ctx.fill();

              if (node.isCenter) {
                ctx.strokeStyle = 'rgba(255,255,255,0.6)';
                ctx.lineWidth = 2;
                ctx.stroke();
              }

              const fontSize = node.isCenter ? 10 : 8;
              ctx.font = `bold ${fontSize}px -apple-system, sans-serif`;
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = '#ffffff';
              ctx.fillText(node.ticker, x, y);
            }}
            linkColor={(link: { color: string }) => link.color}
            cooldownTicks={60}
            onEngineStop={(fg: { zoomToFit: (ms: number, px: number) => void }) => fg?.zoomToFit(300, 40)}
            enableNodeDrag={false}
            enableZoomInteraction={false}
            enablePanInteraction={false}
          />
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-gray-400">
            관계 데이터가 없습니다.
          </div>
        )}
      </div>

      {/* 연결 종목 태그 */}
      {connectedTags.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-2">
            연결 종목 ({graphData?.meta.node_count || 0})
          </p>
          <div className="flex flex-wrap gap-2">
            {connectedTags.map(({ ticker, label }) => (
              <Link
                key={`${ticker}-${label}`}
                href={`/stocks/${ticker}`}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-full bg-gray-100 hover:bg-gray-200 transition"
              >
                <span className="font-medium">{ticker}</span>
                <span className="text-gray-500">{label}</span>
              </Link>
            ))}
            {(graphData?.meta.node_count || 0) > 6 && (
              <Link
                href={`/chainsight/${symbol}`}
                className="inline-flex items-center px-2.5 py-1 text-xs rounded-full bg-blue-50 text-blue-600 hover:bg-blue-100"
              >
                +{(graphData?.meta.node_count || 0) - 6} 더 보기
              </Link>
            )}
          </div>
        </div>
      )}

      {/* 프로파일 요약 */}
      {graphData?.center && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          {graphData.center.growth_stage && (
            <div className="bg-gray-50 rounded-lg p-3">
              <span className="text-gray-500">GrowthStage</span>
              <p className="font-medium mt-0.5">{graphData.center.growth_stage}</p>
            </div>
          )}
          {graphData.center.capital_dna && (
            <div className="bg-gray-50 rounded-lg p-3">
              <span className="text-gray-500">CapitalDNA</span>
              <p className="font-medium mt-0.5">{graphData.center.capital_dna}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
