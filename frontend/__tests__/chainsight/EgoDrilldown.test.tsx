/**
 * EgoDrilldown (⑳-2 S2) — [목록][지도] 토글, 기본=목록, 비-ego=그래프만.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockStore = { centerSymbol: null as string | null };
vi.mock('@/lib/stores/explorationStore', () => ({
  useExplorationStore: () => mockStore,
}));
vi.mock('@/components/chainsight/MarketGraphCanvas', () => ({
  default: () => <div data-testid="market-graph-canvas" />,
}));
vi.mock('@/components/chainsight/RelationCardList', () => ({
  default: () => <div data-testid="relation-card-list" />,
}));

import EgoDrilldown from '@/components/chainsight/EgoDrilldown';

beforeEach(() => {
  mockStore.centerSymbol = null;
});

describe('EgoDrilldown (⑳-2)', () => {
  it('비-ego(centerSymbol 없음): 토글 없이 그래프만', () => {
    mockStore.centerSymbol = null;
    render(<EgoDrilldown />);
    expect(screen.getByTestId('market-graph-canvas')).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: '목록' })).not.toBeInTheDocument();
  });

  it('ego 모드: 토글 존재, 기본 = 목록(카드 리스트)', () => {
    mockStore.centerSymbol = 'NVDA';
    render(<EgoDrilldown />);
    expect(screen.getByRole('tab', { name: '목록' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '지도' })).toBeInTheDocument();
    expect(screen.getByTestId('relation-card-list')).toBeInTheDocument();
    expect(screen.queryByTestId('market-graph-canvas')).not.toBeInTheDocument();
  });

  it('지도 토글 클릭 → 그래프 뷰(기존 동작 보존)', () => {
    mockStore.centerSymbol = 'NVDA';
    render(<EgoDrilldown />);
    fireEvent.click(screen.getByRole('tab', { name: '지도' }));
    expect(screen.getByTestId('market-graph-canvas')).toBeInTheDocument();
    expect(screen.queryByTestId('relation-card-list')).not.toBeInTheDocument();
  });
});
