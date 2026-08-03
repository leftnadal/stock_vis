/**
 * EgoDrilldown — ⑳-2 목록 기본 + ⑳-3 S3-MINDMAP 마인드맵 토글.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockStore = { centerSymbol: null as string | null, selectNode: vi.fn() };
vi.mock('@/lib/stores/explorationStore', () => ({
  useExplorationStore: () => mockStore,
}));
vi.mock('@/components/chainsight/MarketGraphCanvas', () => ({
  default: () => <div data-testid="market-graph-canvas" />,
}));
vi.mock('@/components/chainsight/RelationCardList', () => ({
  default: () => <div data-testid="relation-card-list" />,
}));
vi.mock('@/components/chainsight/MindmapView', () => ({
  default: () => <div data-testid="mindmap-view" />,
}));

import EgoDrilldown from '@/components/chainsight/EgoDrilldown';

beforeEach(() => {
  mockStore.centerSymbol = null;
});

describe('EgoDrilldown', () => {
  it('비-ego(centerSymbol 없음): 토글 없이 그래프만', () => {
    mockStore.centerSymbol = null;
    render(<EgoDrilldown />);
    expect(screen.getByTestId('market-graph-canvas')).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: '목록' })).not.toBeInTheDocument();
  });

  it('ego 모드: 목록/마인드맵 토글 노출, 기본=목록', () => {
    mockStore.centerSymbol = 'NVDA';
    render(<EgoDrilldown />);
    expect(screen.getByRole('tab', { name: '목록' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '마인드맵' })).toBeInTheDocument();
    expect(screen.getByTestId('relation-card-list')).toBeInTheDocument();
    expect(screen.queryByTestId('mindmap-view')).not.toBeInTheDocument();
    // 지도-B 유지: 지도 토글·캔버스 미노출
    expect(screen.queryByRole('tab', { name: '지도' })).not.toBeInTheDocument();
    expect(screen.queryByTestId('market-graph-canvas')).not.toBeInTheDocument();
  });

  it('마인드맵 탭 클릭 → MindmapView 렌더', () => {
    mockStore.centerSymbol = 'NVDA';
    render(<EgoDrilldown />);
    fireEvent.click(screen.getByRole('tab', { name: '마인드맵' }));
    expect(screen.getByTestId('mindmap-view')).toBeInTheDocument();
    expect(screen.queryByTestId('relation-card-list')).not.toBeInTheDocument();
  });
});
