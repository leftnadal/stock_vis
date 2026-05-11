/**
 * Chain Sight 탐색 상태 (Zustand)
 */

import { create } from 'zustand';
import type { TrailNode, Neighbor } from '@/types/chainsight';

interface ExplorationState {
  selectedSector: string | null;
  centerSymbol: string | null;
  trail: TrailNode[];
  historyNodes: string[];
  currentNeighbors: Neighbor[];
  selectedRelationGroup: string | null;
  highlightedChain: string | null;

  selectSector: (sector: string) => void;
  selectNode: (symbol: string, relationFromPrev?: string) => void;
  undoToTrailNode: (depth: number) => void;
  startChainExploration: (sector: string, symbol: string) => void;
  initializeFocusExploration: (sector: string, symbol: string) => void;
  setCurrentNeighbors: (neighbors: Neighbor[]) => void;
  setHighlightedChain: (chainId: string | null) => void;
  reset: () => void;
}

const initialState = {
  selectedSector: null as string | null,
  centerSymbol: null as string | null,
  trail: [] as TrailNode[],
  historyNodes: [] as string[],
  currentNeighbors: [] as Neighbor[],
  selectedRelationGroup: null as string | null,
  highlightedChain: null as string | null,
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

  reset: () => set(initialState),
}));
