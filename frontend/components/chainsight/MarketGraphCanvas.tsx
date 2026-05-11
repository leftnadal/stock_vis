'use client';

import { useRef, useEffect, useMemo, useCallback, useState } from 'react';
import dynamic from 'next/dynamic';
import { useExplorationStore } from '@/lib/stores/explorationStore';
import { useSectorGraph, useNeighbors } from '@/hooks/useMarketView';
import type { MarketNode, MarketEdge, Neighbor, CrossEdge } from '@/types/chainsight';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

// ── 시드 색상 ──
const SEED_COLORS: Record<string, { bg: string; border: string }> = {
  price:    { bg: '#FCEBEB', border: '#E24B4A' },
  volume:   { bg: '#E1F5EE', border: '#1D9E75' },
  relation: { bg: '#E6F1FB', border: '#378ADD' },
  comention: { bg: '#F3E8FF', border: '#9333EA' },
};

// ── 엣지 색상 ──
const EDGE_COLORS: Record<string, string> = {
  SUPPLIES_TO:      '#5DCAA5',
  COMPETES_WITH:    '#F0997B',
  PEER_OF:          '#85B7EB',
  CO_MENTIONED:     '#AFA9EC',
  PRICE_CORRELATED: '#D3D1C7',
};

const NODE_SIZE_MAP = { xl: 14, lg: 11, md: 8, sm: 6 };

interface GraphNode {
  id: string;
  name: string;
  is_seed: boolean;
  seed_type: string | null;
  node_size: string;
  isCenter: boolean;
  isHistory: boolean;
  x?: number;
  y?: number;
}

interface GraphLink {
  source: string;
  target: string;
  type: string;
  truth_score: number | null;
  relation_category: string;
}

export default function MarketGraphCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [containerWidth, setContainerWidth] = useState(800);

  const {
    selectedSector, centerSymbol, historyNodes, highlightedChain,
    selectNode,
  } = useExplorationStore();

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const update = () => setContainerWidth(el.clientWidth);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const { data: sectorData, isLoading: sectorLoading } = useSectorGraph(
    selectedSector && !centerSymbol ? selectedSector : null,
  );
  const { data: neighborData, isLoading: neighborLoading } = useNeighbors(centerSymbol);

  // 데이터 변환
  const { nodes, links } = useMemo(() => {
    if (centerSymbol && neighborData) {
      return buildNeighborGraph(neighborData, centerSymbol, historyNodes);
    }
    if (selectedSector && sectorData) {
      return buildSectorGraph(sectorData, historyNodes);
    }
    return { nodes: [], links: [] };
  }, [centerSymbol, neighborData, selectedSector, sectorData, historyNodes]);

  // d3 force 파라미터 — 노드 수에 따라 간격 동적 조정
  useEffect(() => {
    const fg = graphRef.current;
    if (!fg?.d3Force || nodes.length === 0) return;
    try {
      const n = nodes.length;
      const linkDist = n <= 8 ? 170 : n <= 20 ? 130 : n <= 40 ? 100 : 80;
      const chargeStr = n <= 8 ? -800 : n <= 20 ? -550 : n <= 40 ? -380 : -280;

      const linkForce = fg.d3Force('link') as { distance?: (fn: () => number) => void } | null;
      linkForce?.distance?.(() => linkDist);

      const chargeForce = fg.d3Force('charge') as { strength?: (fn: () => number) => void } | null;
      chargeForce?.strength?.(() => chargeStr);

      fg.d3ReheatSimulation?.();
    } catch {
      // force API 미지원 시 무시
    }
  }, [nodes, links]);

  // 시뮬레이션 안정화 후 모든 노드가 화면에 보이도록 fit
  const handleEngineStop = useCallback(() => {
    graphRef.current?.zoomToFit(400, 80);
  }, []);

  const handleNodeClick = useCallback(
    (node: any) => {
      if (node?.id) selectNode(node.id);
    },
    [selectNode],
  );

  const isLoading = sectorLoading || neighborLoading;
  const isEmpty = !selectedSector && !centerSymbol;

  if (isEmpty) {
    return (
      <div className="flex items-center justify-center h-[400px] bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700">
        <p className="text-gray-500 dark:text-gray-400 text-sm">
          섹터를 선택하세요
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[400px] bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative h-[400px] bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <ForceGraph2D
        ref={graphRef}
        graphData={{ nodes, links }}
        width={containerWidth}
        height={400}
        nodeId="id"
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D) => {
          paintNode(node, ctx, highlightedChain);
        }}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const r = getNodeRadius(node);
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          ctx.fill();
        }}
        linkColor={(link: any) => EDGE_COLORS[link.type] || '#9CA3AF'}
        linkWidth={(link: any) => {
          if (link.truth_score != null) return Math.max(1, link.truth_score / 30);
          return 1;
        }}
        linkLineDash={(link: any) => {
          if (['CO_MENTIONED', 'PRICE_CORRELATED'].includes(link.type)) return [3, 3];
          if (link.type === 'PEER_OF') return [4, 3];
          return [];
        }}
        onNodeClick={handleNodeClick}
        cooldownTicks={100}
        warmupTicks={50}
        d3AlphaDecay={0.035}
        d3VelocityDecay={0.3}
        onEngineStop={handleEngineStop}
      />
    </div>
  );
}

// ── 헬퍼 ──

function getNodeRadius(node: GraphNode): number {
  if (node.isCenter) return 16;
  return NODE_SIZE_MAP[node.node_size as keyof typeof NODE_SIZE_MAP] || 8;
}

function paintNode(node: any, ctx: CanvasRenderingContext2D, highlightedChain: string | null) {
  const r = getNodeRadius(node);
  const { x, y } = node;

  // 히스토리 노드 반투명
  if (node.isHistory) {
    ctx.globalAlpha = 0.4;
  }

  // 배경
  if (node.is_seed && node.seed_type) {
    const colors = SEED_COLORS[node.seed_type] || SEED_COLORS.price;
    ctx.fillStyle = colors.bg;
    ctx.strokeStyle = colors.border;
  } else {
    ctx.fillStyle = '#F3F4F6';
    ctx.strokeStyle = '#D1D5DB';
  }

  ctx.lineWidth = node.isCenter ? 2.5 : 1.5;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, 2 * Math.PI);
  ctx.fill();
  ctx.stroke();

  // 라벨
  ctx.globalAlpha = 1;
  ctx.fillStyle = '#1F2937';
  ctx.font = `${node.isCenter ? 'bold ' : ''}${r > 10 ? 10 : 8}px sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const label = node.id.length > 5 ? node.id.slice(0, 5) : node.id;
  ctx.fillText(label, x, y);

  // 이름 (큰 노드만)
  if (r >= 10 && node.name) {
    ctx.font = '7px sans-serif';
    ctx.fillStyle = '#6B7280';
    const name = node.name.length > 12 ? node.name.slice(0, 12) + '…' : node.name;
    ctx.fillText(name, x, y + r + 8);
  }
}

function buildSectorGraph(
  data: { nodes: MarketNode[]; edges: MarketEdge[] },
  historyNodes: string[],
): { nodes: GraphNode[]; links: GraphLink[] } {
  return {
    nodes: data.nodes.map((n) => ({
      id: n.symbol,
      name: n.name,
      is_seed: n.is_seed,
      seed_type: n.seed_type,
      node_size: n.node_size,
      isCenter: false,
      isHistory: historyNodes.includes(n.symbol),
    })),
    links: data.edges.map((e) => ({
      source: e.source,
      target: e.target,
      type: e.type,
      truth_score: e.truth_score,
      relation_category: e.relation_category,
    })),
  };
}

function buildNeighborGraph(
  data: { center: any; neighbors: Neighbor[]; cross_edges: CrossEdge[] },
  centerSymbol: string,
  historyNodes: string[],
): { nodes: GraphNode[]; links: GraphLink[] } {
  const nodes: GraphNode[] = [
    {
      id: data.center.symbol,
      name: data.center.name,
      is_seed: data.center.is_seed,
      seed_type: data.center.seed_type,
      node_size: 'xl',
      isCenter: true,
      isHistory: false,
    },
    ...data.neighbors.map((n) => ({
      id: n.symbol,
      name: n.name,
      is_seed: n.is_seed,
      seed_type: n.seed_type,
      node_size: 'md' as const,
      isCenter: false,
      isHistory: historyNodes.includes(n.symbol),
    })),
  ];

  const links: GraphLink[] = [
    ...data.neighbors.map((n) => ({
      source: n.relation.direction === 'outbound' ? centerSymbol : n.symbol,
      target: n.relation.direction === 'outbound' ? n.symbol : centerSymbol,
      type: n.relation.type,
      truth_score: n.relation.truth_score,
      relation_category: n.relation.relation_category,
    })),
    ...data.cross_edges.map((ce) => ({
      source: ce.source,
      target: ce.target,
      type: ce.type,
      truth_score: ce.truth_score,
      relation_category: 'truth',
    })),
  ];

  return { nodes, links };
}
