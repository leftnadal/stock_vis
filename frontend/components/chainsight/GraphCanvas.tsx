'use client';

/**
 * Chain Sight 메인 그래프 캔버스
 *
 * react-force-graph-2d + Canvas 렌더링
 * SSR 불가 → dynamic import 필수 (부모에서 처리)
 */

import {
  useRef,
  useCallback,
  useMemo,
  useEffect,
  useState,
  type MutableRefObject,
} from 'react';
import type { GraphResponse, ForceNode, ForceLink, RelationType } from '@/types/chainsight';
import { getRelationStyle, getSectorColor, getNodeRadius } from './graphStyles';

// react-force-graph-2d 타입
type ForceGraphMethods = {
  zoomToFit: (ms?: number, px?: number) => void;
  centerAt: (x: number, y: number, ms?: number) => void;
};

interface GraphCanvasProps {
  data: GraphResponse;
  width: number;
  height: number;
  selectedNode: string | null;
  highlightRelTypes: string[];
  onNodeClick: (ticker: string) => void;
  onNodeHover?: (ticker: string | null) => void;
  ForceGraph2D: React.ComponentType<Record<string, unknown>>;
}

export default function GraphCanvas({
  data,
  width,
  height,
  selectedNode,
  highlightRelTypes,
  onNodeClick,
  onNodeHover,
  ForceGraph2D,
}: GraphCanvasProps) {
  const graphRef = useRef<ForceGraphMethods>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // ── 데이터 변환: API → ForceGraph 형태 ──
  const graphData = useMemo(() => {
    if (!data?.center) return { nodes: [], links: [] };

    const nodeMap = new Map<string, ForceNode>();

    // center
    nodeMap.set(data.center.ticker, {
      id: data.center.ticker,
      ticker: data.center.ticker,
      name: data.center.name || data.center.ticker,
      sector: data.center.sector || '',
      market_cap: data.center.market_cap || 0,
      pagerank: data.center.pagerank_score || 1,
      isCenter: true,
      depth: 0,
    });

    // neighbors — ticker가 없는 노드(Sector/Industry/Theme) 제외
    for (const node of data.nodes) {
      if (!node.ticker || nodeMap.has(node.ticker)) continue;
      nodeMap.set(node.ticker, {
        id: node.ticker,
        ticker: node.ticker,
        name: node.name || node.ticker,
        sector: node.sector || '',
        market_cap: node.market_cap || 0,
        pagerank: node.pagerank_score || 0.5,
        isCenter: false,
        depth: 1,
      });
    }

    // edges → links
    const links: ForceLink[] = [];
    for (const edge of data.edges) {
      if (!nodeMap.has(edge.from) || !nodeMap.has(edge.to)) continue;

      const displayType = edge.derived_type || edge.type;
      const style = getRelationStyle(displayType);

      links.push({
        source: edge.from,
        target: edge.to,
        relType: displayType as RelationType,
        displayType,
        label: style.label,
        color: style.color,
        width: style.width,
        dash: style.dash,
      });
    }

    return {
      nodes: Array.from(nodeMap.values()),
      links,
    };
  }, [data]);

  // ── d3 force 설정 (노드 간격 넓히기) ──
  useEffect(() => {
    const fg = graphRef.current as unknown as {
      d3Force: (name: string, force?: unknown) => unknown;
      d3ReheatSimulation: () => void;
    };
    if (!fg?.d3Force) return;

    try {
      const linkForce = fg.d3Force('link') as { distance?: (fn: () => number) => void } | null;
      if (linkForce?.distance) linkForce.distance(() => 180);

      const chargeForce = fg.d3Force('charge') as { strength?: (fn: () => number) => void } | null;
      if (chargeForce?.strength) chargeForce.strength(() => -600);

      fg.d3ReheatSimulation?.();
    } catch {
      // force API 미지원 시 무시
    }
  }, [graphData]);

  // ── 시뮬레이션 안정화 후 zoomToFit ──
  const handleEngineStop = useCallback(() => {
    graphRef.current?.zoomToFit(400, 60);
  }, []);

  // ── 노드 Canvas 렌더링 ──
  const paintNode = useCallback(
    (node: ForceNode, ctx: CanvasRenderingContext2D) => {
      const r = getNodeRadius(node.isCenter, node.pagerank);
      const x = (node as unknown as { x: number }).x;
      const y = (node as unknown as { y: number }).y;

      // 필터링 시 비활성 노드 투명도 조절
      const isActive = highlightRelTypes.length === 0 || node.isCenter ||
        graphData.links.some(
          l =>
            highlightRelTypes.includes(l.relType) &&
            ((l.source === node.id || (l.source as unknown as ForceNode)?.id === node.id) ||
             (l.target === node.id || (l.target as unknown as ForceNode)?.id === node.id))
        );
      const alpha = isActive ? 1.0 : 0.2;

      ctx.globalAlpha = alpha;

      // 배경 원
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = getSectorColor(node.sector);
      ctx.fill();

      // 선택/호버 테두리
      if (node.ticker === selectedNode || node.ticker === hoveredNode) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.stroke();
      } else if (node.isCenter) {
        ctx.strokeStyle = 'rgba(255,255,255,0.6)';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // 라벨
      const fontSize = node.isCenter ? 11 : 9;
      ctx.font = `bold ${fontSize}px -apple-system, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(node.ticker, x, y);

      ctx.globalAlpha = 1.0;
    },
    [selectedNode, hoveredNode, highlightRelTypes, graphData.links]
  );

  // ── 엣지 Canvas 렌더링 ──
  const paintLink = useCallback(
    (link: ForceLink, ctx: CanvasRenderingContext2D) => {
      const src = link.source as unknown as { x: number; y: number };
      const tgt = link.target as unknown as { x: number; y: number };
      if (!src?.x || !tgt?.x) return;

      const isHighlighted = highlightRelTypes.length === 0 ||
        highlightRelTypes.includes(link.relType);

      ctx.globalAlpha = isHighlighted ? 0.8 : 0.1;

      ctx.beginPath();
      if (link.dash) {
        ctx.setLineDash(link.dash);
      } else {
        ctx.setLineDash([]);
      }
      ctx.strokeStyle = link.color;
      ctx.lineWidth = link.width;
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.globalAlpha = 1.0;
    },
    [highlightRelTypes]
  );

  return (
    <ForceGraph2D
      ref={graphRef as MutableRefObject<unknown>}
      width={width}
      height={height}
      graphData={graphData}
      nodeId="id"
      nodeCanvasObject={paintNode}
      nodePointerAreaPaint={(node: ForceNode, color: string, ctx: CanvasRenderingContext2D) => {
        const r = getNodeRadius(node.isCenter, node.pagerank);
        const x = (node as unknown as { x: number }).x;
        const y = (node as unknown as { y: number }).y;
        ctx.beginPath();
        ctx.arc(x, y, r + 4, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
      }}
      linkCanvasObject={paintLink}
      onNodeClick={(node: ForceNode) => onNodeClick(node.ticker)}
      onNodeHover={(node: ForceNode | null) => {
        setHoveredNode(node?.ticker || null);
        onNodeHover?.(node?.ticker || null);
      }}
      cooldownTicks={100}
      warmupTicks={50}
      onEngineStop={handleEngineStop}
      enableNodeDrag={true}
      enableZoomInteraction={true}
      linkDirectionalArrowLength={0}
      d3AlphaDecay={0.04}
      d3VelocityDecay={0.25}
      nodeVal={(node: ForceNode) => node.isCenter ? 30 : 8}
    />
  );
}
