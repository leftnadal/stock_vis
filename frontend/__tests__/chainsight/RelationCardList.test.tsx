/**
 * RelationCardList (⑳-2 S2 → ⑳-G 정직화) — 섹션 분리·등급 배지·근거·확인일·절단·빈 상태.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { EgoGraphResponse, EgoEdge } from '@/types/chainsight';

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

function egde(partial: Partial<EgoEdge> & { target: string }): EgoEdge {
  return {
    source: 'NVDA',
    relation_type: 'PEER_OF',
    truth_score: 85,
    evidence_count: 0,
    last_mentioned: '2026-07-20',
    trend: { direction: 'flat', delta: 0, points: [] },
    grade: 'confirmed',
    grade_source: 'market_peer',
    basis_summary: '',
    last_observed_at: '2026-07-20',
    ...partial,
  };
}

function wrap(edges: EgoEdge[], total: number): EgoGraphResponse {
  return {
    center: { symbol: 'NVDA', name: 'NVIDIA' },
    nodes: edges.map((e) => ({ symbol: e.target, name: `${e.target} Inc`, sector: 'Tech' })),
    edges,
    meta: { total_edges: total, returned: edges.length, filtered_by: { min_score: 0, types: null, limit: 50, trend_window: 12 } },
  };
}

function manyPeers(n: number): EgoEdge[] {
  return Array.from({ length: n }, (_, i) =>
    egde({ target: `SYM${String(i).padStart(2, '0')}`, evidence_count: i, grade: 'confirmed' }),
  );
}

beforeEach(() => {
  selectNode.mockClear();
  mockStore.centerSymbol = 'NVDA';
  egoResult = { data: undefined, isLoading: false, isError: false, refetch: vi.fn() };
});

describe('RelationCardList (⑳-G 정직화)', () => {
  it('유형별 섹션 분리: 공급망·경쟁·Peer 헤더', () => {
    egoResult = {
      data: wrap([
        egde({ target: 'TSM', relation_type: 'SUPPLIES_TO', grade_source: 'sec_filing', basis_summary: 'SEC 10-K: foundry' }),
        egde({ target: 'ANET', relation_type: 'COMPETES_WITH', grade_source: 'sec_filing', basis_summary: 'SEC 10-K: compete' }),
        egde({ target: 'AMD', relation_type: 'PEER_OF' }),
      ], 3),
      isLoading: false, isError: false, refetch: vi.fn(),
    };
    render(<RelationCardList />);
    expect(screen.getByRole('heading', { name: '공급망' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '경쟁' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Peer' })).toBeInTheDocument();
  });

  it('등급 배지 렌더(확정 · 동종 / 관찰 · 뉴스)', () => {
    egoResult = {
      data: wrap([
        egde({ target: 'AMD', grade: 'confirmed', grade_source: 'market_peer' }),
        egde({ target: 'CMX', relation_type: 'CO_MENTIONED', grade: 'observed', grade_source: 'co_mention', truth_score: 0, basis_summary: '뉴스 동시출현 4회' }),
      ], 2),
      isLoading: false, isError: false, refetch: vi.fn(),
    };
    render(<RelationCardList />);
    expect(screen.getByText('확정 · 동종')).toBeInTheDocument();
    expect(screen.getByText('관찰 · 뉴스')).toBeInTheDocument();
  });

  it('공시 관계는 basis_summary 노출·근거건수 미표기(0건 오해 차단)', () => {
    egoResult = {
      data: wrap([
        egde({ target: 'TSM', relation_type: 'SUPPLIES_TO', grade_source: 'sec_filing', evidence_count: 0, basis_summary: 'SEC 10-K: We utilize foundries such as TSMC' }),
      ], 1),
      isLoading: false, isError: false, refetch: vi.fn(),
    };
    render(<RelationCardList />);
    expect(screen.getByText(/SEC 10-K: We utilize foundries/)).toBeInTheDocument();
    expect(screen.queryByText(/근거 0건/)).not.toBeInTheDocument();
    expect(screen.queryByText(/뉴스 근거/)).not.toBeInTheDocument();
  });

  it('뉴스 관계는 "뉴스 근거 N건" 표기', () => {
    egoResult = {
      data: wrap([
        egde({ target: 'CMX', relation_type: 'CO_MENTIONED', grade_source: 'co_mention', evidence_count: 3, basis_summary: '뉴스 동시출현 7회' }),
      ], 1),
      isLoading: false, isError: false, refetch: vi.fn(),
    };
    render(<RelationCardList />);
    expect(screen.getByText(/뉴스 근거 3건/)).toBeInTheDocument();
  });

  it('확인일(last_observed_at) 라벨 노출', () => {
    egoResult = {
      data: wrap([egde({ target: 'AMD', last_observed_at: '2026-06-20' })], 1),
      isLoading: false, isError: false, refetch: vi.fn(),
    };
    render(<RelationCardList />);
    expect(screen.getByText(/확인일 2026-06-20/)).toBeInTheDocument();
  });

  it('절단 총량 명시 + 더 보기', () => {
    egoResult = { data: wrap(manyPeers(50), 224), isLoading: false, isError: false, refetch: vi.fn() };
    render(<RelationCardList />);
    expect(screen.getByText(/전체 224개 관계 중/)).toBeInTheDocument();
    expect(screen.getByText(/상위 50개까지 제공/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /더 보기/ })).toBeInTheDocument();
  });

  it('더 보기 클릭 시 표시 개수 증가', () => {
    egoResult = { data: wrap(manyPeers(50), 224), isLoading: false, isError: false, refetch: vi.fn() };
    render(<RelationCardList />);
    const before = screen.getAllByRole('button', { name: /관계 카드/ }).length;
    fireEvent.click(screen.getByRole('button', { name: /더 보기/ }));
    const after = screen.getAllByRole('button', { name: /관계 카드/ }).length;
    expect(after).toBeGreaterThan(before);
  });

  it('빈 이웃: GraphStatePanel empty-neighbors', () => {
    egoResult = { data: wrap([], 0), isLoading: false, isError: false, refetch: vi.fn() };
    render(<RelationCardList />);
    expect(screen.getByTestId('graph-state-empty-neighbors')).toBeInTheDocument();
  });

  it('오류: GraphStatePanel load-error', () => {
    egoResult = { data: undefined, isLoading: false, isError: true, refetch: vi.fn() };
    render(<RelationCardList />);
    expect(screen.getByTestId('graph-state-load-error')).toBeInTheDocument();
  });

  it('카드 클릭 → selectNode(target, relation_type)', () => {
    egoResult = { data: wrap([egde({ target: 'AMD' })], 1), isLoading: false, isError: false, refetch: vi.fn() };
    render(<RelationCardList />);
    fireEvent.click(screen.getByRole('button', { name: /관계 카드/ }));
    expect(selectNode).toHaveBeenCalledWith('AMD', 'PEER_OF');
  });
});
