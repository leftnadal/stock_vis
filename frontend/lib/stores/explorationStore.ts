/**
 * Chain Sight 탐색 상태 (Zustand)
 */

import { create } from 'zustand';
import type { TrailNode, Neighbor, RelationType } from '@/types/chainsight';

// ── 관계 칩 기본 ON 상태 (§2-2 명세) ──
// 공급망(SUPPLIES_TO, CUSTOMER_OF), 경쟁(COMPETES_WITH), Peer(PEER_OF), 뉴스(CO_MENTIONED) = ON
// 가격상관(PRICE_CORRELATED), 테마(HAS_THEME) = OFF
export const DEFAULT_ENABLED_REL_TYPES: Set<RelationType> = new Set([
  'SUPPLIES_TO',
  'CUSTOMER_OF',
  'COMPETES_WITH',
  'PEER_OF',
  'CO_MENTIONED',
]);

interface ExplorationState {
  selectedSector: string | null;
  centerSymbol: string | null;
  trail: TrailNode[];
  historyNodes: string[];
  currentNeighbors: Neighbor[];
  selectedRelationGroup: string | null;
  highlightedChain: string | null;
  // § 2-2 관계 필터 칩 상태
  enabledRelTypes: Set<RelationType>;

  selectSector: (sector: string) => void;
  selectNode: (symbol: string, relationFromPrev?: string) => void;
  undoToTrailNode: (depth: number) => void;
  startChainExploration: (sector: string, symbol: string) => void;
  initializeFocusExploration: (sector: string, symbol: string) => void;
  setCurrentNeighbors: (neighbors: Neighbor[]) => void;
  setHighlightedChain: (chainId: string | null) => void;
  toggleRelType: (type: RelationType) => void;
  enableAllRelTypes: () => void;
  disableAllRelTypes: () => void;
  reset: () => void;
}

// ALL_REL_TYPES: 전체 켜기 시 사용
export const ALL_REL_TYPES: RelationType[] = [
  'SUPPLIES_TO',
  'CUSTOMER_OF',
  'COMPETES_WITH',
  'PEER_OF',
  'CO_MENTIONED',
  'PRICE_CORRELATED',
  'HAS_THEME',
];

const initialState = {
  selectedSector: null as string | null,
  centerSymbol: null as string | null,
  trail: [] as TrailNode[],
  historyNodes: [] as string[],
  currentNeighbors: [] as Neighbor[],
  selectedRelationGroup: null as string | null,
  highlightedChain: null as string | null,
  enabledRelTypes: DEFAULT_ENABLED_REL_TYPES,
};

export const useExplorationStore = create<ExplorationState>()((set) => ({
  ...initialState,

  selectSector: (sector) =>
    set({
      selectedSector: sector,
      centerSymbol: null,
      trail: [{ symbol: sector, type: 'sector', depth: 0 }],
      historyNodes: [],
      currentNeighbors: [],
      highlightedChain: null,
    }),

  selectNode: (symbol, relationFromPrev) =>
    set((state) => {
      const prevCenter = state.centerSymbol;
      const newHistory = prevCenter
        ? [prevCenter, ...state.historyNodes].slice(0, 3)
        : state.historyNodes;
      const depth = state.trail.length;
      return {
        centerSymbol: symbol,
        trail: [
          ...state.trail,
          {
            symbol,
            type: 'stock' as const,
            depth,
            relation_from_prev: relationFromPrev,
          },
        ],
        historyNodes: newHistory,
        highlightedChain: null,
      };
    }),

  undoToTrailNode: (depth) =>
    set((state) => {
      const sliced = state.trail.slice(0, depth + 1);
      const last = sliced[sliced.length - 1];
      return {
        trail: sliced,
        centerSymbol: last?.type === 'stock' ? last.symbol : null,
        historyNodes: [],
        highlightedChain: null,
      };
    }),

  startChainExploration: (sector, symbol) =>
    set({
      selectedSector: sector,
      centerSymbol: symbol,
      trail: [
        { symbol: sector, type: 'sector', depth: 0 },
        { symbol, type: 'stock', depth: 1 },
      ],
      historyNodes: [],
      highlightedChain: null,
    }),

  initializeFocusExploration: (sector, symbol) =>
    set({
      selectedSector: sector,
      centerSymbol: symbol,
      trail: [
        { symbol: sector, type: 'sector', depth: 0 },
        { symbol, type: 'stock', depth: 1 },
      ],
      historyNodes: [],
      currentNeighbors: [],
      highlightedChain: null,
    }),

  setCurrentNeighbors: (neighbors) => set({ currentNeighbors: neighbors }),

  setHighlightedChain: (chainId) => set({ highlightedChain: chainId }),

  // § 2-4 관계 칩 토글 — 해당 타입을 켜거나 끔
  toggleRelType: (type) =>
    set((state) => {
      const next = new Set(state.enabledRelTypes);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return { enabledRelTypes: next };
    }),

  // § 2-4 전체 켜기
  enableAllRelTypes: () => set({ enabledRelTypes: new Set(ALL_REL_TYPES) }),

  // § 2-4 전체 끄기
  disableAllRelTypes: () => set({ enabledRelTypes: new Set<RelationType>() }),

  reset: () => set(initialState),
}));
