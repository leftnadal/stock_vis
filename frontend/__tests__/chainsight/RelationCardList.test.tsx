/**
 * RelationCardList (⑳-2 S2) — ego 카드 리스트: 정렬·절단 총량·빈 상태·카드 클릭.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { EgoGraphResponse } from '@/types/chainsight';

const selectNode = vi.fn();
const mockStore = { centerSymbol: 'NVDA' as string | null, selectNode };
let egoResult: { data?: EgoGraphResponse; isLoading: boolean; isError: boolean; refetch: () => void };

vi.mock('@/lib/stores/explorationStore', () => ({
  useExplorationStore: () => mockStore,
}));
vi.mock('@/hooks/useMarketView', () => ({
  useEgo: () => egoResult,
}));

import RelationCardList from '@/components/chainsight/RelationCardList';

function makeEgo(edgeCount: number, total: number): EgoGraphResponse {
  const edges = Array.from({ length: edgeCount }, (_, i) => ({
    source: 'NVDA',
    target: `SYM${i}`,
    relation_type: 'PEER_OF',
    truth_score: 100 - i, // 내림차순 확인용
    evidence_count: i,
    last_mentioned: '2026-07-20',
    trend: { direction: 'flat' as const, delta: 0, points: [] },
  }));
  return {
    center: { symbol: 'NVDA', name: 'NVIDIA' },
    nodes: edges.map((e) => ({ symbol: e.target, name: `${e.target} Inc`, sector: 'Tech' })),
    edges,
    meta: { total_edges: total, returned: edgeCount, filtered_by: { min_score: 0, types: null, limit: 50, trend_window: 12 } },
  };
}

beforeEach(() => {
  selectNode.mockClear();
  mockStore.centerSymbol = 'NVDA';
  egoResult = { data: undefined, isLoading: false, isError: false, refetch: vi.fn() };
});

describe('RelationCardList (⑳-2)', () => {
  it('신뢰도 내림차순 기본 정렬 + 배지 렌더', () => {
    egoResult = { data: makeEgo(3, 3), isLoading: false, isError: false, refetch: vi.fn() };
    render(<RelationCardList />);
    const cards = screen.getAllByRole('button', { name: /관계 카드/ });
    expect(cards[0]).toHaveTextContent('SYM0'); // truth 100 최상단
    expect(screen.getAllByText('Peer').length).toBe(3); // 배지
  });

  it('절단 총량 명시: 전체 M개 중 N개 (loaded < total)', () => {
    egoResult = { data: makeEgo(50, 224), isLoading: false, isError: false, refetch: vi.fn() };
    render(<RelationCardList />);
    expect(screen.getByText(/전체 224개 관계 중/)).toBeInTheDocument();
    expect(screen.getByText(/상위 50개까지 제공/)).toBeInTheDocument();
    // 기본 12개 표시 + 더 보기
    expect(screen.getByRole('button', { name: /더 보기/ })).toBeInTheDocument();
  });

  it('더 보기 클릭 시 표시 개수 증가', () => {
    egoResult = { data: makeEgo(50, 224), isLoading: false, isError: false, refetch: vi.fn() };
    render(<RelationCardList />);
    const before = screen.getAllByRole('button', { name: /관계 카드/ }).length;
    fireEvent.click(screen.getByRole('button', { name: /더 보기/ }));
    const after = screen.getAllByRole('button', { name: /관계 카드/ }).length;
    expect(after).toBeGreaterThan(before);
  });

  it('빈 이웃: GraphStatePanel empty-neighbors', () => {
    egoResult = { data: makeEgo(0, 0), isLoading: false, isError: false, refetch: vi.fn() };
    render(<RelationCardList />);
    expect(screen.getByTestId('graph-state-empty-neighbors')).toBeInTheDocument();
  });

  it('오류: GraphStatePanel load-error', () => {
    egoResult = { data: undefined, isLoading: false, isError: true, refetch: vi.fn() };
    render(<RelationCardList />);
    expect(screen.getByTestId('graph-state-load-error')).toBeInTheDocument();
  });

  it('카드 클릭 → selectNode(target, relation_type)', () => {
    egoResult = { data: makeEgo(2, 2), isLoading: false, isError: false, refetch: vi.fn() };
    render(<RelationCardList />);
    fireEvent.click(screen.getAllByRole('button', { name: /관계 카드/ })[0]);
    expect(selectNode).toHaveBeenCalledWith('SYM0', 'PEER_OF');
  });
});
