'use client';

import { useRef, useEffect, useMemo, useCallback, useState } from 'react';
import dynamic from 'next/dynamic';
import { useExplorationStore } from '@/lib/stores/explorationStore';
import { useSectorGraph, useNeighbors, useSeedData } from '@/hooks/useMarketView';
import type { MarketNode, MarketEdge, Neighbor, CrossEdge } from '@/types/chainsight';
import {
  computeRadialPositions,
  inferSecondaryNeighbors,
  type RadialNeighbor,
} from './radialLayout';
import NodeTooltip, { type TooltipNodeInfo } from './NodeTooltip';
import NodeContextMenu, { type ContextMenuNodeInfo } from './NodeContextMenu';
import RelationLegend from './RelationLegend';
import { CHANGE_TEXT } from '@/components/common/colorSemantics';

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
  /** §FE-PR-3: 이 노드가 center와 연결된 관계 타입 (radialLayout 좌표 계산에 사용) */
  relType?: string;
  x?: number;
  y?: number;
  /** d3 고정 좌표 — §8-1 fx/fy 수동 주입 */
  fx?: number;
  fy?: number;
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

  // §FE-PR-4: 툴팁 상태
  const [tooltipNode, setTooltipNode] = useState<TooltipNodeInfo | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const tooltipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // §FE-PR-4: 컨텍스트 메뉴 상태
  const [contextMenuNode, setContextMenuNode] = useState<ContextMenuNodeInfo | null>(null);
  const [contextMenuPos, setContextMenuPos] = useState({ x: 0, y: 0 });
  const [contextMenuVisible, setContextMenuVisible] = useState(false);

  // §FE-PR-4: 모바일 탭 상태 (첫 탭=툴팁, 두 번째 탭=center)
  const lastTappedNodeRef = useRef<string | null>(null);
  const lastTapTimeRef = useRef<number>(0);
  // 롱프레스: pointerdown 시작 시각
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const longPressPosRef = useRef({ x: 0, y: 0 });

  // 컨테이너 DOMRect — 툴팁·메뉴 경계 계산용
  const [containerRect, setContainerRect] = useState<DOMRect | null>(null);

  // §8-1 우회법: graphData 변경 시 fx/fy 초기화 문제 → nodePositions ref 별도 관리
  // onEngineStop 직후 한 번 주입하고, 이후 d3ReheatSimulation 미호출
  // graphData 재생성(다른 종목 클릭) 시에도 이 ref에서 fx/fy를 복구
  const nodePositionsRef = useRef<Map<string, { fx: number; fy: number }>>(new Map());
  // 현재 center 심볼 추적 — 변경 감지 시 positions 재계산
  const positionsCenterRef = useRef<string | null>(null);
  // fx/fy 이미 주입되었는지 추적 (한 번만 zoomToFit 실행)
  const positionsInjectedRef = useRef<boolean>(false);

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
    selectSector,
  } = useExplorationStore();

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const update = () => {
      setContainerWidth(el.clientWidth);
      setContainerRect(el.getBoundingClientRect());
    };
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

  const { data: seedData } = useSeedData();
  const { data: sectorData, isLoading: sectorLoading } = useSectorGraph(
    selectedSector && !centerSymbol ? selectedSector : null,
  );
  const { data: neighborData, isLoading: neighborLoading } = useNeighbors(centerSymbol);

  // 데이터 변환
  const { nodes, links } = useMemo(() => {
    if (centerSymbol && neighborData) {
      const result = buildNeighborGraph(neighborData, centerSymbol, historyNodes);

      // §FE-PR-3: center가 바뀌었으면 방사형 좌표를 재계산하여 ref에 저장
      // graphData 객체를 새로 생성해도 ref는 살아있으므로 §8-1 문제 우회
      if (positionsCenterRef.current !== centerSymbol) {
        positionsCenterRef.current = centerSymbol;
        positionsInjectedRef.current = false;

        // 이웃 노드를 RadialNeighbor 형태로 변환
        const radialNeighbors: RadialNeighbor[] = result.nodes
          .filter((n) => !n.isCenter)
          .map((n) => ({
            symbol: n.id,
            relType: n.relType ?? 'CO_MENTIONED',
            depth: 1, // 기본 1차 이웃
          }));

        // cross_edges에서 2차 이웃 추론
        const neighborSymbols = new Set(radialNeighbors.map((r) => r.symbol));
        const secondaries = inferSecondaryNeighbors(
          neighborSymbols,
          centerSymbol,
          neighborData.cross_edges.map((ce) => ({ source: ce.source, target: ce.target })),
        );

        // 2차 이웃도 RadialNeighbor에 추가 (relType 없으면 CO_MENTIONED fallback)
        const crossEdgeRelTypes = new Map<string, string>();
        for (const ce of neighborData.cross_edges) {
          if (secondaries.has(ce.source)) crossEdgeRelTypes.set(ce.source, ce.type);
          if (secondaries.has(ce.target)) crossEdgeRelTypes.set(ce.target, ce.type);
        }
        for (const sym of secondaries) {
          radialNeighbors.push({
            symbol: sym,
            relType: crossEdgeRelTypes.get(sym) ?? 'CO_MENTIONED',
            depth: 2,
          });
        }

        // computeRadialPositions는 순수 함수 — center=원점, 이웃=방사형 배치
        const positions = computeRadialPositions(centerSymbol, radialNeighbors, {
          ring1Radius: 160,
          ring2Radius: 280,
        });
        nodePositionsRef.current = positions;
      }

      return result;
    }
    if (selectedSector && sectorData) {
      // 섹터 그래프: center 개념 없음 → 방사형 미적용, 기존 force 유지
      positionsCenterRef.current = null;
      positionsInjectedRef.current = false;
      nodePositionsRef.current = new Map();
      return buildSectorGraph(sectorData, historyNodes);
    }
    return { nodes: [], links: [] };
  }, [centerSymbol, neighborData, selectedSector, sectorData, historyNodes]);

  // §FE-PR-4: nodeMap — symbol → GraphNode (툴팁/메뉴에서 노드 정보 조회)
  const nodeMap = useMemo(() => {
    const map = new Map<string, GraphNode>();
    for (const n of nodes) map.set(n.id, n);
    return map;
  }, [nodes]);

  // §FE-PR-4: 이웃 관계 맵 — symbol → relType (center와의 관계, neighborData에서 파생)
  const neighborRelMap = useMemo(() => {
    const map = new Map<string, string>();
    if (!neighborData) return map;
    for (const nb of neighborData.neighbors) {
      map.set(nb.symbol, nb.relation.type);
    }
    return map;
  }, [neighborData]);

  // §FE-PR-4: 이웃 시드 사유 맵 — symbol → seed_reasons[]
  const neighborSeedReasonsMap = useMemo(() => {
    const map = new Map<string, string[]>();
    if (!neighborData) return map;
    // center 노드 포함
    map.set(neighborData.center.symbol, neighborData.center.seed_reasons ?? []);
    for (const nb of neighborData.neighbors) {
      map.set(nb.symbol, nb.seed_reasons ?? []);
    }
    return map;
  }, [neighborData]);

  // §FE-PR-4: 섹터 그래프용 시드 사유/관계 맵 (sectorData.nodes)
  const sectorNodeInfoMap = useMemo(() => {
    const map = new Map<string, { sector: string; seedReasons: string[]; seedType: string | null }>();
    if (!sectorData) return map;
    for (const n of sectorData.nodes) {
      map.set(n.symbol, {
        sector: n.sector,
        seedReasons: n.seed_reasons ?? [],
        seedType: n.seed_type,
      });
    }
    return map;
  }, [sectorData]);

  // §FE-PR-4: 툴팁 닫기 헬퍼
  const hideTooltip = useCallback(() => {
    if (tooltipTimerRef.current) {
      clearTimeout(tooltipTimerRef.current);
      tooltipTimerRef.current = null;
    }
    setTooltipVisible(false);
    setTooltipNode(null);
  }, []);

  // §FE-PR-4: 컨텍스트 메뉴 닫기 헬퍼
  const closeContextMenu = useCallback(() => {
    setContextMenuVisible(false);
    setContextMenuNode(null);
  }, []);

  // §FE-PR-4: 노드의 TooltipNodeInfo 빌더
  const buildTooltipInfo = useCallback((symbol: string): TooltipNodeInfo | null => {
    const graphNode = nodeMap.get(symbol);
    if (!graphNode) return null;

    if (centerSymbol) {
      // 이웃 그래프 모드
      const relType = symbol === centerSymbol ? undefined : neighborRelMap.get(symbol);
      const seedReasons = neighborSeedReasonsMap.get(symbol) ?? [];
      return {
        symbol,
        name: graphNode.name,
        sector: neighborData?.neighbors.find((n) => n.symbol === symbol)?.sector
          ?? neighborData?.center.sector
          ?? undefined,
        seedReasons,
        relType,
        seedType: graphNode.seed_type,
      };
    } else {
      // 섹터 그래프 모드
      const info = sectorNodeInfoMap.get(symbol);
      return {
        symbol,
        name: graphNode.name,
        sector: info?.sector,
        seedReasons: info?.seedReasons ?? [],
        relType: undefined,       // 섹터 그래프에서는 관계 라벨 없음
        seedType: info?.seedType ?? null,
      };
    }
  }, [nodeMap, centerSymbol, neighborRelMap, neighborSeedReasonsMap, neighborData, sectorNodeInfoMap]);

  // §FE-PR-4: 캔버스 내 픽셀 좌표를 forceGraph 좌표에서 변환
  // react-force-graph-2d onNodeHover 콜백이 canvas 픽셀 좌표를 제공하지 않으므로
  // graphRef에서 screen 좌표 변환 (graph2ScreenCoords)
  const getCanvasPos = useCallback((nodeObj: any): { x: number; y: number } => {
    const fg = graphRef.current;
    if (!fg?.graph2ScreenCoords) return { x: 0, y: 0 };
    return fg.graph2ScreenCoords(nodeObj.x ?? 0, nodeObj.y ?? 0) as { x: number; y: number };
  }, []);

  // d3 force 파라미터 — 노드 수에 따라 charge strength 동적 조정
  // §1-6: 각도는 fx/fy로 고정, 동일 구간 내 분산은 charge에 위임
  // §8-1: 방사형 모드에서는 d3ReheatSimulation 미호출 (onEngineStop에서 fx/fy 주입 후 불변 유지)
  useEffect(() => {
    const fg = graphRef.current;
    if (!fg?.d3Force || nodes.length === 0) return;
    try {
      const n = nodes.length;
      const isRadialMode = positionsCenterRef.current !== null;

      if (isRadialMode) {
        // §1-6 권고치: 방사형 모드에서 charge는 분산용으로만 사용
        // linkForce distance 영향력 약화 (fx/fy가 거리 결정권을 가져가므로)
        const chargeStr = n <= 8 ? -600 : n <= 20 ? -400 : n <= 40 ? -280 : -200;

        const linkForce = fg.d3Force('link') as {
          distance?: (fn: () => number) => void;
          strength?: (fn: () => number) => void;
        } | null;
        // linkForce strength를 낮춰서 fx/fy 고정 좌표에 간섭 최소화
        linkForce?.strength?.(() => 0.1);

        const chargeForce = fg.d3Force('charge') as {
          strength?: (fn: () => number) => void;
        } | null;
        chargeForce?.strength?.(() => chargeStr);

        // §8-1: 방사형 모드에서는 d3ReheatSimulation 미호출
        // (onEngineStop 이후 한 번만 fx/fy 주입 → 이후 불변)
      } else {
        // 섹터 그래프: 기존 force-directed 유지
        const linkDist = n <= 8 ? 170 : n <= 20 ? 130 : n <= 40 ? 100 : 80;
        const chargeStr = n <= 8 ? -800 : n <= 20 ? -550 : n <= 40 ? -380 : -280;

        const linkForce = fg.d3Force('link') as {
          distance?: (fn: () => number) => void;
        } | null;
        linkForce?.distance?.(() => linkDist);

        const chargeForce = fg.d3Force('charge') as {
          strength?: (fn: () => number) => void;
        } | null;
        chargeForce?.strength?.(() => chargeStr);

        fg.d3ReheatSimulation?.();
      }
    } catch {
      // force API 미지원 시 무시
    }
  }, [nodes, links]);

  // §FE-PR-3 §8-1: onEngineStop 직후 한 번만 fx/fy 주입 → d3ReheatSimulation 미호출
  // 시뮬레이션이 cooldown 완료 후 발화 → 이 시점에 노드 객체에 fx/fy 직접 주입
  // 이후 graphData가 새 객체로 교체되어도 nodePositionsRef에서 복구 가능
  const handleEngineStop = useCallback(() => {
    const fg = graphRef.current;
    if (!fg) return;

    const positions = nodePositionsRef.current;
    const isRadialMode = positionsCenterRef.current !== null;

    if (isRadialMode && positions.size > 0 && !positionsInjectedRef.current) {
      // §8-1: graphData의 노드 객체에 직접 fx/fy 주입
      // react-force-graph-2d는 노드 객체를 직접 참조하므로 이 방식으로 고정
      const graphData = fg.graphData?.() as { nodes: any[] } | undefined;
      if (graphData?.nodes) {
        for (const node of graphData.nodes) {
          const pos = positions.get(node.id);
          if (pos !== undefined) {
            node.fx = pos.fx;
            node.fy = pos.fy;
          }
        }
      }

      positionsInjectedRef.current = true;
      // §8-1: d3ReheatSimulation 호출 금지 — fx/fy 주입 후 시뮬레이션 재가동 없음
    }

    // 모든 노드가 화면에 보이도록 fit (한 번만)
    fg.zoomToFit?.(400, 80);
  }, []);

  const handleNodeClick = useCallback(
    (node: any) => {
      if (node?.id) selectNode(node.id);
    },
    [selectNode],
  );

  // §FE-PR-4: 우클릭 컨텍스트 메뉴
  const handleNodeRightClick = useCallback((node: any, event: MouseEvent) => {
    event.preventDefault();
    if (!node?.id) return;

    const graphNode = nodeMap.get(node.id);
    if (!graphNode) return;

    const pos = getCanvasPos(node);
    setContextMenuPos(pos);
    setContextMenuNode({ symbol: node.id, name: graphNode.name });
    setContextMenuVisible(true);

    // 우클릭 시 툴팁 닫기
    hideTooltip();
  }, [nodeMap, getCanvasPos, hideTooltip]);

  // §FE-PR-4: 모바일 롱프레스 + 두 번째 탭 처리
  // react-force-graph-2d의 onNodeClick을 모바일에서도 사용하되,
  // 첫 탭/두 번째 탭 구분은 별도 래퍼로 처리
  const handleNodeClickMobile = useCallback((node: any) => {
    if (!node?.id) return;

    const now = Date.now();
    const TAP_DOUBLE_THRESHOLD = 500; // ms 이내 같은 노드 두 번째 탭 = center 전환

    const isMobile = typeof window !== 'undefined' && window.matchMedia('(pointer: coarse)').matches;

    if (isMobile) {
      if (
        lastTappedNodeRef.current === node.id &&
        now - lastTapTimeRef.current < TAP_DOUBLE_THRESHOLD
      ) {
        // 두 번째 탭: center 전환
        selectNode(node.id);
        lastTappedNodeRef.current = null;
        hideTooltip();
      } else {
        // 첫 탭: 툴팁 표시
        lastTappedNodeRef.current = node.id;
        lastTapTimeRef.current = now;

        const info = buildTooltipInfo(node.id);
        if (info) {
          const pos = getCanvasPos(node);
          setTooltipPos(pos);
          setTooltipNode(info);
          setTooltipVisible(true);

          // 모바일: 다른 곳 탭 시 닫힘은 외부 클릭으로 자동 처리
        }
      }
    } else {
      // 데스크톱: 일반 좌클릭 = center 전환
      selectNode(node.id);
    }
  }, [selectNode, buildTooltipInfo, getCanvasPos, hideTooltip]);

  // § 7: 노드 호버 핸들러 + §FE-PR-4 툴팁 (200ms 지연)
  const handleNodeHover = useCallback((node: any) => {
    setHoveredNode(node?.id ?? null);

    // 툴팁 타이머 초기화
    if (tooltipTimerRef.current) {
      clearTimeout(tooltipTimerRef.current);
      tooltipTimerRef.current = null;
    }

    if (!node) {
      // 호버 해제: 즉시 툴팁 숨김
      setTooltipVisible(false);
      setTooltipNode(null);
      return;
    }

    // 200ms 지연 후 툴팁 표시 (§3-2 명세)
    const info = buildTooltipInfo(node.id);
    if (!info) return;

    const pos = getCanvasPos(node);
    setTooltipPos(pos);
    setTooltipNode(info);

    tooltipTimerRef.current = setTimeout(() => {
      setTooltipVisible(true);
    }, 200);
  }, [buildTooltipInfo, getCanvasPos]);

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

  // § 4-3: 인기 섹터 3개 — |pct_change| 절댓값 기준 상위 3개
  const popularSectors = useMemo(() => {
    if (!seedData?.sector_summary) return [];
    return [...seedData.sector_summary]
      .sort((a, b) => Math.abs(b.pct_change) - Math.abs(a.pct_change))
      .slice(0, 3);
  }, [seedData]);

  if (isEmpty) {
    // § 4-1: 빈 상태 카피 + § 4-2: SVG 장식 일러스트 + § 4-3: CTA 버튼
    return (
      <div className="flex flex-col items-center justify-center h-[560px] bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 px-4 gap-6">
        {/* § 4-2 SVG 장식 그래프 일러스트 (정적, 실제 데이터 없음) */}
        <svg
          width="160"
          height="120"
          viewBox="0 0 160 120"
          aria-hidden
          className="opacity-60"
        >
          {/* 외곽 점 장식 */}
          {[
            [80, 8], [120, 20], [148, 50], [140, 90], [80, 112],
            [20, 90], [12, 50], [40, 20],
          ].map(([cx, cy], i) => (
            <circle key={i} cx={cx} cy={cy} r="3" fill="#D1D5DB" className="dark:fill-gray-600" />
          ))}
          {/* 연결선 */}
          {[
            [60, 50, 100, 50], [80, 40, 60, 50], [80, 40, 100, 50],
            [60, 50, 50, 75], [100, 50, 110, 75],
            [80, 40, 80, 20],
          ].map(([x1, y1, x2, y2], i) => (
            <line
              key={i}
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke="#E5E7EB"
              strokeWidth="1.5"
              className="dark:stroke-gray-700"
            />
          ))}
          {/* 보조 노드 */}
          {[
            [60, 50], [100, 50], [50, 75], [110, 75],
          ].map(([cx, cy], i) => (
            <circle key={i} cx={cx} cy={cy} r="8"
              fill="#F3F4F6" stroke="#D1D5DB" strokeWidth="1.5"
              className="dark:fill-gray-700 dark:stroke-gray-600"
            />
          ))}
          {/* 최상단 보조 */}
          <circle cx="80" cy="20" r="6"
            fill="#F3F4F6" stroke="#D1D5DB" strokeWidth="1"
            className="dark:fill-gray-700 dark:stroke-gray-600"
          />
          {/* center 노드 — 연파랑 브랜드 힌트 */}
          <circle cx="80" cy="40" r="13"
            fill="#DBEAFE" stroke="#93C5FD" strokeWidth="2"
            className="dark:fill-blue-900/40 dark:stroke-blue-400"
          />
          {/* center 점 */}
          <circle cx="80" cy="40" r="4" fill="#3B82F6" />
        </svg>

        {/* § 4-1 메인 카피 */}
        <div className="text-center space-y-1.5">
          <p className="text-base font-medium text-gray-800 dark:text-gray-200">
            오늘 시장에서 연결된 종목들을 탐색하세요
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            섹터를 선택하면 관계 지도가 펼쳐집니다
          </p>
        </div>

        {/* § 4-3 인기 섹터 빠른 접근 버튼 — |pct_change| 상위 3개 */}
        {popularSectors.length > 0 && (
          <div className="flex flex-wrap justify-center gap-3">
            {popularSectors.map((s) => (
              <button
                key={s.sector}
                type="button"
                onClick={() => selectSector(s.sector)}
                className={[
                  'flex flex-col items-start',
                  'w-[110px] min-h-[68px] px-3 py-2',
                  'rounded-xl border border-gray-200 dark:border-gray-700',
                  'bg-white dark:bg-gray-800',
                  'text-left',
                  'hover:border-blue-400 hover:bg-blue-50 dark:hover:border-blue-500 dark:hover:bg-blue-900/20',
                  'transition-colors duration-150',
                  'shadow-sm',
                ].join(' ')}
              >
                <span className="text-xs font-semibold text-gray-800 dark:text-gray-100 leading-tight">
                  {s.sector_display}
                </span>
                <span
                  className={[
                    'mt-1 text-[11px] font-medium tabular-nums',
                    s.pct_change >= 0 ? CHANGE_TEXT.up : CHANGE_TEXT.down,
                  ].join(' ')}
                >
                  {s.pct_change >= 0 ? '+' : ''}{s.pct_change.toFixed(2)}%
                </span>
                <span className="mt-0.5 text-[10px] text-gray-400 dark:text-gray-500">
                  {s.seed_count}개 시드
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (isLoading) {
    // § 4-2 로딩 스켈레톤: 노드·엣지 placeholder 펄스 + 섹터명 안내 텍스트
    return (
      <div className="relative h-[560px] bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* 스켈레톤 SVG — 노드 8개 + 엣지 8개 랜덤 배치 */}
        <svg
          className="absolute inset-0 w-full h-full"
          aria-hidden
        >
          {/* 엣지 placeholder */}
          {[
            [180, 200, 280, 160], [280, 160, 380, 220], [380, 220, 300, 300],
            [300, 300, 200, 320], [200, 320, 180, 200], [280, 160, 300, 300],
            [180, 200, 300, 300], [380, 220, 200, 320],
          ].map(([x1, y1, x2, y2], i) => (
            <line
              key={i}
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke="#E5E7EB"
              strokeWidth="1.5"
              className="dark:stroke-gray-700 animate-pulse"
            />
          ))}
          {/* 노드 placeholder */}
          {[
            [180, 200, 12], [280, 160, 18], [380, 220, 12],
            [300, 300, 12], [200, 320, 10], [130, 280, 10],
            [420, 300, 10], [320, 380, 10],
          ].map(([cx, cy, r], i) => (
            <circle
              key={i}
              cx={cx} cy={cy} r={r}
              fill="#E5E7EB"
              className="dark:fill-gray-700 animate-pulse"
              style={{ animationDelay: `${i * 0.12}s`, animationDuration: '1.4s' }}
            />
          ))}
        </svg>
        {/* 로딩 텍스트 */}
        <div className="absolute bottom-8 left-0 right-0 flex justify-center">
          <p className="text-sm text-gray-400 dark:text-gray-500 animate-pulse">
            {selectedSector ? `${selectedSector} 섹터 관계 지도를 불러오는 중...` : '관계 지도를 불러오는 중...'}
          </p>
        </div>
      </div>
    );
  }

  return (
    // § 5-1 메인 캔버스 560px (기존 400px → 560px)
    // § 7 cross-fade: opacity transition 200ms (스켈레톤→실제 그래프)
    <div ref={containerRef} className="relative h-[560px] bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden transition-opacity duration-200 opacity-100">
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
        onNodeClick={handleNodeClickMobile}
        onNodeRightClick={handleNodeRightClick}
        onNodeHover={handleNodeHover}
        cooldownTicks={100}
        warmupTicks={50}
        d3AlphaDecay={0.035}
        d3VelocityDecay={0.3}
        onEngineStop={handleEngineStop}
      />

      {/* §FE-PR-4: 툴팁 overlay */}
      <NodeTooltip
        node={tooltipNode}
        canvasX={tooltipPos.x}
        canvasY={tooltipPos.y}
        containerRect={containerRect}
        visible={tooltipVisible}
      />

      {/* §FE-PR-4: 컨텍스트 메뉴 overlay */}
      <NodeContextMenu
        node={contextMenuNode}
        x={contextMenuPos.x}
        y={contextMenuPos.y}
        containerRect={containerRect}
        visible={contextMenuVisible}
        onClose={closeContextMenu}
        onExplore={(symbol) => selectNode(symbol)}
      />

      {/* §FE-PR-5 §5-3: 범례 — 캔버스 내 좌하단 absolute overlay */}
      <RelationLegend />
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
      // center는 §FE-PR-3: fx=0, fy=0 — nodePositionsRef에서 주입
    },
    ...data.neighbors.map((n) => ({
      id: n.symbol,
      name: n.name,
      is_seed: n.is_seed,
      seed_type: n.seed_type,
      node_size: 'md' as const,
      isCenter: false,
      isHistory: historyNodes.includes(n.symbol),
      // §FE-PR-3: relType 메타데이터 보존 → computeRadialPositions에 전달
      relType: n.relation.type,
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
