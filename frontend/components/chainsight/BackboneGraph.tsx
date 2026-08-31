'use client';

/**
 * RC-C-1 backbone 그래프 캔버스 (GraphCanvas 패턴 — props 주입형 ForceGraph2D).
 *
 * 노드 = 중심성 top 심볼(pagerank 크기), 엣지 = 유도 부분그래프.
 * θ 기준 실선/점선: score >= theta → 실선, 미만 → 점선(dash). 현재 API 는 θ≥0.85
 * 엣지만 반환(전부 실선) — 점선 분기는 sub-θ 엣지 확장(2-1 계약) 대비 준비.
 * SSR 불가 → dynamic import 는 부모(page)에서 ssr:false 로 처리.
 */

import { useMemo, useCallback, type MutableRefObject, useRef } from 'react';
import type { BackboneSymbol, BackboneEdge } from '@/types/backbone';

type ForceGraphMethods = { zoomToFit: (ms?: number, px?: number) => void };

interface BackboneNode {
  id: string;
  symbol: string;
  pagerank: number;
  degree: number;
}

interface BackboneLink {
  source: string;
  target: string;
  score: number;
  category: string;
  color: string;
  width: number;
  dash?: number[];       // undefined = 실선(θ≥), 값 존재 = 점선(sub-θ)
  edge: BackboneEdge;    // 원 엣지(클릭 시 근거 바로 전달)
}

interface BackboneGraphProps {
  topSymbols: BackboneSymbol[];
  edges: BackboneEdge[];
  theta: number;
  width: number;
  height: number;
  selectedEdgeKey: string | null;
  onEdgeSelect: (edge: BackboneEdge) => void;
  ForceGraph2D: React.ComponentType<Record<string, unknown>>;
}

export function edgeKey(e: { symbol_a: string; symbol_b: string }): string {
  return e.symbol_a <= e.symbol_b
    ? `${e.symbol_a}|${e.symbol_b}`
    : `${e.symbol_b}|${e.symbol_a}`;
}

const CATEGORY_COLOR: Record<string, string> = {
  truth: '#58A6FF',
  market: '#F0883E',
};

export default function BackboneGraph({
  topSymbols,
  edges,
  theta,
  width,
  height,
  selectedEdgeKey,
  onEdgeSelect,
  ForceGraph2D,
}: BackboneGraphProps) {
  const graphRef = useRef<ForceGraphMethods>(null);

  const graphData = useMemo(() => {
    const nodeIds = new Set(topSymbols.map((s) => s.symbol));
    const nodes: BackboneNode[] = topSymbols.map((s) => ({
      id: s.symbol,
      symbol: s.symbol,
      pagerank: s.pagerank,
      degree: s.degree,
    }));

    const links: BackboneLink[] = [];
    for (const e of edges) {
      // 유도 부분그래프: 양 끝이 모두 top 심볼일 때만.
      if (!nodeIds.has(e.symbol_a) || !nodeIds.has(e.symbol_b)) continue;
      const isSolid = e.score >= theta;
      links.push({
        source: e.symbol_a,
        target: e.symbol_b,
        score: e.score,
        category: e.category,
        color: CATEGORY_COLOR[e.category] ?? '#8B949E',
        width: 1 + e.score * 2,
        dash: isSolid ? undefined : [4, 4],
        edge: e,
      });
    }
    return { nodes, links };
  }, [topSymbols, edges, theta]);

  const maxPr = useMemo(
    () => Math.max(1e-9, ...topSymbols.map((s) => s.pagerank)),
    [topSymbols],
  );

  const paintNode = useCallback(
    (node: BackboneNode, ctx: CanvasRenderingContext2D) => {
      const r = 6 + (node.pagerank / maxPr) * 14;
      const x = (node as unknown as { x: number }).x;
      const y = (node as unknown as { y: number }).y;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = '#238636';
      ctx.fill();
      ctx.font = 'bold 9px -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(node.symbol, x, y);
    },
    [maxPr],
  );

  const paintLink = useCallback(
    (link: BackboneLink, ctx: CanvasRenderingContext2D) => {
      const src = link.source as unknown as { x: number; y: number };
      const tgt = link.target as unknown as { x: number; y: number };
      if (!src?.x || !tgt?.x) return;
      const isSelected = edgeKey(link.edge) === selectedEdgeKey;
      ctx.globalAlpha = isSelected ? 1.0 : 0.6;
      ctx.beginPath();
      ctx.setLineDash(link.dash ?? []);
      ctx.strokeStyle = isSelected ? '#ffffff' : link.color;
      ctx.lineWidth = isSelected ? link.width + 1.5 : link.width;
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1.0;
    },
    [selectedEdgeKey],
  );

  return (
    <ForceGraph2D
      ref={graphRef as MutableRefObject<unknown>}
      width={width}
      height={height}
      graphData={graphData}
      nodeId="id"
      nodeCanvasObject={paintNode}
      linkCanvasObject={paintLink}
      onLinkClick={(link: BackboneLink) => onEdgeSelect(link.edge)}
      cooldownTicks={100}
      warmupTicks={50}
      onEngineStop={() => graphRef.current?.zoomToFit(400, 60)}
      enableNodeDrag={true}
      linkDirectionalArrowLength={0}
      d3AlphaDecay={0.04}
      d3VelocityDecay={0.25}
    />
  );
}
