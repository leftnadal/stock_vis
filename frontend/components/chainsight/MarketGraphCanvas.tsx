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

// ── 엣지 색상 (§6-1 명세 계층) ──
const EDGE_COLORS: Record<string, string> = {
  SUPPLIES_TO:      '#F97316',  // 오렌지 — 1계층 구조적 비즈니스
  CUSTOMER_OF:      '#F97316',  // 오렌지 — 1계층 구조적 비즈니스 (공급망 묶음)
  COMPETES_WITH:    '#EF4444',  // 빨강  — 1계층 구조적 비즈니스
  PEER_OF:          '#3B82F6',  // 파랑  — 2계층 구조적 비교
  CO_MENTIONED:     '#A855F7',  // 보라  — 3계층 시장 신호
  HAS_THEME:        '#14B8A6',  // 틸   — 3계층 시장 신호
  PRICE_CORRELATED: '#9CA3AF',  // 회색  — 3계층 시장 신호
};

// § 6-1 엣지 굵기
const EDGE_WIDTHS: Record<string, number> = {
  SUPPLIES_TO:      3,
  CUSTOMER_OF:      3,
  COMPETES_WITH:    2.5,
  PEER_OF:          2,
  CO_MENTIONED:     1.5,
  HAS_THEME:        1,
  PRICE_CORRELATED: 1,
};

// § 6-1 엣지 점선 패턴
const EDGE_DASHES: Record<string, number[]> = {
  CO_MENTIONED:     [5, 4],
  HAS_THEME:        [8, 4],
  PRICE_CORRELATED: [3, 3],
};

// § 2-4 비활성 엣지 alpha (칩 토글)
const ALPHA_ACTIVE   = 0.85;
const ALPHA_INACTIVE = 0.15;

// § 6-1 약한 관계(3계층) 활성 시 alpha — 강한 관계보다 낮게 차등 적용
const ALPHA_WEAK_ACTIVE = 0.55;
const WEAK_REL_TYPES = new Set(['CO_MENTIONED', 'HAS_THEME', 'PRICE_CORRELATED']);

// § 1-5 노드 크기 위계 (3단계 고대비)
// center=28px, 1차 이웃: xl=20, lg=17, md=14 (pagerank 비례), 2차=8~12
const NODE_SIZE_MAP = { xl: 20, lg: 17, md: 14, sm: 10 };

// § 7 호버 애니메이션 duration (ms)
const HOVER_FADE_DURATION = 100;

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

// § 7: 호버 alpha를 부드럽게 보간하는 헬퍼
function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * Math.min(1, Math.max(0, t));
}

export default function MarketGraphCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [containerWidth, setContainerWidth] = useState(800);

  // § 7: hoveredNode 상태 — 호버 중인 노드 ID
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  // § 7: 호버 애니메이션 진행값 (0.0~1.0), 애니메이션 프레임 ref
  const hoverProgressRef = useRef<number>(0);
  const hoverAnimFrameRef = useRef<number | null>(null);
  const hoverStartTimeRef = useRef<number | null>(null);

  const {
    selectedSector, centerSymbol, historyNodes, highlightedChain,
    enabledRelTypes,
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

  // § 7: 호버 fade-in/dim 애니메이션 (100ms)
  useEffect(() => {
    const direction = hoveredNode !== null ? 1 : -1; // 1=dim-in, -1=dim-out

    if (hoverAnimFrameRef.current !== null) {
      cancelAnimationFrame(hoverAnimFrameRef.current);
    }

    const startProgress = hoverProgressRef.current;
    hoverStartTimeRef.current = null;

    const animate = (ts: number) => {
      if (hoverStartTimeRef.current === null) hoverStartTimeRef.current = ts;
      const elapsed = ts - hoverStartTimeRef.current;
      const t = Math.min(elapsed / HOVER_FADE_DURATION, 1);

      hoverProgressRef.current = direction > 0
        ? lerp(startProgress, 1, t)
        : lerp(startProgress, 0, t);

      // 그래프를 다시 그리도록 강제 리렌더
      graphRef.current?.refresh?.();

      if (t < 1) {
        hoverAnimFrameRef.current = requestAnimationFrame(animate);
      } else {
        hoverAnimFrameRef.current = null;
      }
    };

    hoverAnimFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (hoverAnimFrameRef.current !== null) {
        cancelAnimationFrame(hoverAnimFrameRef.current);
      }
    };
  }, [hoveredNode]);

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

  // § 7: 노드 호버 핸들러
  const handleNodeHover = useCallback((node: any) => {
    setHoveredNode(node?.id ?? null);
  }, []);

  const isLoading = sectorLoading || neighborLoading;
  const isEmpty = !selectedSector && !centerSymbol;

  // § 7 링크 alpha 합성 계산 — 칩 토글(chip) + 호버 dim(hover) 누적
  //
  // 규칙:
  //  1) 칩이 비활성이면 항상 ALPHA_INACTIVE (0.15) — 호버로도 완전 숨김은 안 함
  //  2) 칩이 활성 + 호버 없음 → chipAlpha (강한=0.85, 약한=0.55)
  //  3) 칩이 활성 + 호버 있음
  //     - 호버된 노드에 연결된 엣지 → 1.0 (강조)
  //     - 비연결 엣지 → ALPHA_INACTIVE (0.15, dim)
  //     - 칩 비활성 엣지는 호버 연결이어도 ALPHA_INACTIVE 유지 (칩 우선)
  const getLinkAlpha = useCallback(
    (link: any): number => {
      const isActive = enabledRelTypes.has(link.type);
      if (enabledRelTypes.size === 0) return 0; // 모두 끔: 투명

      // § 6-1 약한 엣지 vs 강한 엣지 chip alpha
      const chipAlpha = isActive
        ? (WEAK_REL_TYPES.has(link.type) ? ALPHA_WEAK_ACTIVE : ALPHA_ACTIVE)
        : ALPHA_INACTIVE;

      // § 7 호버 dim — hoveredNode 없으면 칩 alpha만 적용
      const progress = hoverProgressRef.current;
      if (hoveredNode === null || progress === 0) return chipAlpha;

      // 호버 중: 연결된 링크면 1.0, 아니면 0.15 (progress에 따라 보간)
      const srcId = typeof link.source === 'object' ? link.source.id : link.source;
      const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
      const isConnectedToHovered = srcId === hoveredNode || tgtId === hoveredNode;

      if (isActive) {
        // 활성 칩: 연결→1.0 강조, 비연결→0.15 dim (보간)
        const hoverTargetAlpha = isConnectedToHovered ? 1.0 : ALPHA_INACTIVE;
        return lerp(chipAlpha, hoverTargetAlpha, progress);
      } else {
        // 비활성 칩: 호버와 무관하게 0.15 유지
        return ALPHA_INACTIVE;
      }
    },
    [enabledRelTypes, hoveredNode],
  );

  if (isEmpty) {
    return (
      // § 5-1 빈 상태 높이 통일: 560px
      <div className="flex items-center justify-center h-[560px] bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700">
        <p className="text-gray-500 dark:text-gray-400 text-sm">
          섹터를 선택하세요
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      // § 5-1 로딩 상태 높이 통일: 560px
      <div className="flex items-center justify-center h-[560px] bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    // § 5-1 메인 캔버스 560px (기존 400px → 560px)
    <div ref={containerRef} className="relative h-[560px] bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <ForceGraph2D
        ref={graphRef}
        graphData={{ nodes, links }}
        width={containerWidth}
        height={560}
        nodeId="id"
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D) => {
          // § 7: 호버 dim — 호버 중이면 비연결 노드 alpha 감소
          const progress = hoverProgressRef.current;
          let nodeAlpha: number | undefined;
          if (hoveredNode !== null && progress > 0) {
            // hoveredNode 본인 또는 직접 이웃인지 확인
            const isHoveredSelf = node.id === hoveredNode;
            const isNeighbor = links.some((l) => {
              const srcId = typeof l.source === 'object' ? (l.source as any).id : l.source;
              const tgtId = typeof l.target === 'object' ? (l.target as any).id : l.target;
              return (srcId === hoveredNode && tgtId === node.id) ||
                     (tgtId === hoveredNode && srcId === node.id);
            });
            const targetAlpha = isHoveredSelf || isNeighbor ? 1.0 : ALPHA_INACTIVE;
            // 현재 노드의 기본 alpha (히스토리=0.4, 나머지=1.0)
            const baseAlpha = node.isHistory ? 0.4 : 1.0;
            nodeAlpha = lerp(baseAlpha, targetAlpha, progress);
          }
          paintNode(node, ctx, highlightedChain, nodeAlpha);
        }}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          // § 1-5: center는 28px, 호버 영역도 동일하게
          const r = getNodeRadius(node);
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          ctx.fill();
        }}
        linkColor={(link: any) => {
          // § 6-1 + § 7: 칩 토글 alpha + 호버 dim alpha 합성
          const alpha = getLinkAlpha(link);
          if (alpha <= 0) return 'rgba(0,0,0,0)';
          const baseColor = EDGE_COLORS[link.type] || '#9CA3AF';
          const hex = baseColor.replace('#', '');
          const rr = parseInt(hex.substring(0, 2), 16);
          const gg = parseInt(hex.substring(2, 4), 16);
          const bb = parseInt(hex.substring(4, 6), 16);
          return `rgba(${rr},${gg},${bb},${alpha.toFixed(3)})`;
        }}
        linkWidth={(link: any) => {
          // § 6-1 엣지 굵기 적용
          return EDGE_WIDTHS[link.type] ?? 1;
        }}
        linkLineDash={(link: any) => {
          // § 6-1 점선 패턴 적용
          return EDGE_DASHES[link.type] ?? [];
        }}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
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

// § 1-5: 노드 크기 위계 — center=28px (Level 0)
function getNodeRadius(node: GraphNode): number {
  if (node.isCenter) return 28;
  return NODE_SIZE_MAP[node.node_size as keyof typeof NODE_SIZE_MAP] || 10;
}

// § 6-2: 섹터 색상 매핑 (center 노드 glow용)
function getSectorFillColor(node: GraphNode): string {
  if (node.is_seed && node.seed_type) {
    return SEED_COLORS[node.seed_type]?.bg ?? '#F3F4F6';
  }
  return '#F3F4F6';
}

function getSectorStrokeColor(node: GraphNode): string {
  if (node.is_seed && node.seed_type) {
    return SEED_COLORS[node.seed_type]?.border ?? '#D1D5DB';
  }
  return '#D1D5DB';
}

// § 1-5 + § 6-2: paintNode — center는 glow halo + 흰 링 3px
// nodeAlpha: undefined이면 기본 alpha 적용, 숫자이면 호버 dim 적용
function paintNode(
  node: any,
  ctx: CanvasRenderingContext2D,
  highlightedChain: string | null,
  nodeAlpha?: number,
) {
  const r = getNodeRadius(node);
  const { x, y } = node;

  // 히스토리 노드 기본 반투명 (호버 dim이 없을 때)
  const baseAlpha = node.isHistory ? 0.4 : 1.0;
  ctx.globalAlpha = nodeAlpha !== undefined ? nodeAlpha : baseAlpha;

  const fillColor  = getSectorFillColor(node);
  const strokeColor = getSectorStrokeColor(node);

  if (node.isCenter) {
    // § 6-2 center 노드: shadowBlur glow halo 먼저 그린 뒤 원 칠
    ctx.shadowColor = '#FFFFFF';
    ctx.shadowBlur  = 8;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle = fillColor;
    ctx.fill();
    ctx.shadowBlur = 0; // glow 끄기

    // § 1-5 흰색 외곽선 3px
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth   = 3;
    ctx.stroke();
  } else {
    // 일반 노드
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fillStyle   = fillColor;
    ctx.strokeStyle = strokeColor;
    // § 1-5 Level1: 흰색 1.5px, Level2: 없음 (node_size sm = 10px 이하는 외곽선 생략)
    ctx.lineWidth   = r >= 14 ? 1.5 : 0.5;
    ctx.fill();
    if (r >= 14) {
      ctx.strokeStyle = '#FFFFFF';
      ctx.stroke();
    } else {
      ctx.stroke(); // 연한 원 테두리 유지 (가시성)
    }
  }

  // 라벨 — alpha를 1로 리셋하지 않고 노드 alpha 위에 그림
  ctx.fillStyle = '#1F2937';
  ctx.font = `${node.isCenter ? 'bold ' : ''}${r > 14 ? 11 : r > 10 ? 9 : 7}px sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  // center는 ticker 그대로, 나머지는 최대 5자
  const label = node.isCenter
    ? node.id
    : (node.id.length > 5 ? node.id.slice(0, 5) : node.id);
  ctx.fillText(label, x, y);

  // 이름 (큰 노드만 — center 포함)
  if (r >= 14 && node.name) {
    ctx.font = '8px sans-serif';
    ctx.fillStyle = node.isCenter ? '#374151' : '#6B7280';
    const name = node.name.length > 14 ? node.name.slice(0, 14) + '…' : node.name;
    ctx.fillText(name, x, y + r + 10);
  }

  // globalAlpha 초기화
  ctx.globalAlpha = 1;
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
