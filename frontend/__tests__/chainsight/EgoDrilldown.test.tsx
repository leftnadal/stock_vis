/**
 * EgoDrilldown (⑳-2 S2) — [목록][지도] 토글, 기본=목록, 비-ego=그래프만.
 */
import { render, screen } from '@testing-library/react';
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

  // ⑳-3 S2 D-3 (지도-B): ego 모드에서 [지도] 토글 접힘 → 목록(RelationCardList)만 노출.
  it('ego 모드: 지도-B로 토글 없이 목록만(지도 진입 제거)', () => {
    mockStore.centerSymbol = 'NVDA';
    render(<EgoDrilldown />);
    expect(screen.getByTestId('relation-card-list')).toBeInTheDocument();
    // 지도 토글/캔버스 미노출(코드는 보존, MAP_ENABLED=false)
    expect(screen.queryByRole('tab', { name: '지도' })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: '목록' })).not.toBeInTheDocument();
    expect(screen.queryByTestId('market-graph-canvas')).not.toBeInTheDocument();
  });
});
