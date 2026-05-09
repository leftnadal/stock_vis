import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// --- mocks (컴포넌트 import 전에 선언) ---

const mockExplorationStore = {
  selectedSector: null as string | null,
  centerSymbol: null as string | null,
  selectNode: vi.fn(),
};

vi.mock('@/lib/stores/explorationStore', () => ({
  useExplorationStore: () => mockExplorationStore,
}));

vi.mock('@/hooks/useMarketView', () => ({
  useSeedData: () => ({ data: { seeds: mockSeedList } }),
  useNeighbors: (symbol: string | null) => {
    if (!symbol) return { data: undefined, isLoading: false, isError: false };
    // 상태를 테스트별로 오버라이드
    return mockNeighborResult;
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    back: vi.fn(),
    replace: vi.fn(),
  }),
}));

let mockNeighborResult = {
  data: undefined as unknown,
  isLoading: false,
  isError: false,
};

let mockSeedList: Array<Record<string, unknown>> = [];

import RelationCardPanel from '@/components/chainsight/RelationCardPanel';

beforeEach(() => {
  mockExplorationStore.selectedSector = null;
  mockExplorationStore.centerSymbol = null;
  mockExplorationStore.selectNode = vi.fn();
  mockNeighborResult = { data: undefined, isLoading: false, isError: false };
  mockSeedList = [];
});

describe('RelationCardPanel', () => {
  it('섹터/center가 모두 없으면 빈 상태 메시지를 표시한다', () => {
    render(<RelationCardPanel />);

    expect(screen.getByText(/섹터를 선택하면 대표 시드 카드가 표시됩니다/)).toBeInTheDocument();
  });

  it('centerSymbol이 있고 로딩 중이면 스피너를 표시한다', () => {
    mockExplorationStore.selectedSector = 'Technology';
    mockExplorationStore.centerSymbol = 'AAPL';
    mockNeighborResult = { data: undefined, isLoading: true, isError: false };

    render(<RelationCardPanel />);

    expect(screen.getByText(/관계 데이터를 불러오는 중/)).toBeInTheDocument();
  });

  it('centerSymbol이 있고 에러 시 에러 메시지를 표시한다', () => {
    mockExplorationStore.selectedSector = 'Technology';
    mockExplorationStore.centerSymbol = 'AAPL';
    mockNeighborResult = { data: undefined, isLoading: false, isError: true };

    render(<RelationCardPanel />);

    expect(screen.getByText(/관계 데이터를 불러오지 못했습니다/)).toBeInTheDocument();
  });

  it('selectedSector만 있고 centerSymbol이 없으면 시드 카드를 표시한다', () => {
    mockExplorationStore.selectedSector = 'Technology';
    mockExplorationStore.centerSymbol = null;
    mockSeedList = [
      {
        symbol: 'NVDA',
        name: 'NVIDIA',
        sector: 'Technology',
        seed_type: 'price',
        seed_reasons: ['price_top5'],
        daily_return: 5.2,
        volume_ratio: 2.3,
      },
    ];

    render(<RelationCardPanel />);

    expect(screen.getByText('NVDA')).toBeInTheDocument();
    expect(screen.getByText('NVIDIA')).toBeInTheDocument();
    // REASON_LABELS['price_top5'] === '수익률 상위 이상치'
    expect(screen.getByText(/수익률 상위 이상치/)).toBeInTheDocument();
    // 탐색 시작 버튼
    expect(screen.getByText('여기서 탐색')).toBeInTheDocument();
  });

  it('selectedSector에 시드가 없으면 빈 메시지를 표시한다', () => {
    mockExplorationStore.selectedSector = 'Energy';
    mockExplorationStore.centerSymbol = null;
    mockSeedList = [
      {
        symbol: 'NVDA',
        name: 'NVIDIA',
        sector: 'Technology',
        seed_type: 'price',
        seed_reasons: ['price_top5'],
        daily_return: 5.2,
        volume_ratio: 2.3,
      },
    ];

    render(<RelationCardPanel />);

    expect(screen.getByText(/이 섹터에 시드 노드가 없습니다/)).toBeInTheDocument();
  });
});
