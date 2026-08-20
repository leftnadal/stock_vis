/**
 * MindmapTreeBoard (CS-P5-FE-CARD B3) — 업종 2단 아코디언(기본 접힘) + 검색 필터 + 카드 클릭 포커스.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { MindmapTreeResponse } from '@/types/chainsight';

const mockPush = vi.fn();
let mockSymbolParam: string | null = null;

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => ({ get: (key: string) => (key === 'symbol' ? mockSymbolParam : null) }),
}));

vi.mock('lucide-react', () => ({
  ArrowLeft: ({ className }: { className?: string }) => <span data-testid="icon-arrow-left" className={className} />,
}));

let treeResult: { data?: MindmapTreeResponse; isLoading: boolean; isError: boolean; refetch: () => void };
vi.mock('@/hooks/useMindmap', () => ({
  useMindmapTree: () => treeResult,
  useMindmapCard: () => ({ data: undefined, isLoading: true, isError: false, refetch: vi.fn() }),
}));

import MindmapTreeBoard from '@/components/chainsight/MindmapTreeBoard';

function tree(): MindmapTreeResponse {
  return {
    stock_total: 3,
    sector_count: 2,
    gate_definition: 'serving_layer=evidence AND relation_type∈SEC4종',
    sectors: [
      {
        sector: 'TECHNOLOGY',
        stock_count: 2,
        industry_count: 1,
        industries: [
          {
            industry: 'Semiconductors',
            stock_count: 2,
            cards: [
              { ticker: 'NVDA', name: 'NVIDIA', gate_conn_count: 5, group_signal_count: 2 },
              { ticker: 'AMD', name: 'Advanced Micro Devices', gate_conn_count: 0, group_signal_count: 0 },
            ],
          },
        ],
      },
      {
        sector: '미분류',
        stock_count: 1,
        industry_count: 1,
        industries: [
          {
            industry: '미분류',
            stock_count: 1,
            cards: [{ ticker: 'ZZZ', name: 'Zzz Corp', gate_conn_count: 1, group_signal_count: 0 }],
          },
        ],
      },
    ],
  };
}

beforeEach(() => {
  mockPush.mockClear();
  mockSymbolParam = null;
  treeResult = { data: tree(), isLoading: false, isError: false, refetch: vi.fn() };
});

describe('MindmapTreeBoard (CS-P5-FE-CARD B3)', () => {
  it('sector 헤더 렌더 + 기본 접힘(카드 미노출)', () => {
    render(<MindmapTreeBoard />);
    expect(screen.getByText('TECHNOLOGY')).toBeInTheDocument();
    expect(screen.getByText('미분류')).toBeInTheDocument();
    // 기본 접힘 — industry/카드 미노출
    expect(screen.queryByText('Semiconductors')).not.toBeInTheDocument();
    expect(screen.queryByText('NVDA')).not.toBeInTheDocument();
  });

  it('sector 클릭 → industry 펼침 → industry 클릭 → 카드 그리드 렌더', () => {
    render(<MindmapTreeBoard />);
    fireEvent.click(screen.getByText('TECHNOLOGY'));
    expect(screen.getByText('Semiconductors')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Semiconductors'));
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    expect(screen.getByText('연결 5')).toBeInTheDocument();
    expect(screen.getByText('그룹 2')).toBeInTheDocument();
  });

  it('검색어 입력 시 매칭 sector/industry만 자동 펼쳐짐', () => {
    render(<MindmapTreeBoard />);
    fireEvent.change(screen.getByLabelText('티커 또는 종목명 검색'), { target: { value: 'nvda' } });
    expect(screen.getByText('Semiconductors')).toBeInTheDocument();
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    // 미매칭 카드(AMD)는 검색 중 숨김
    expect(screen.queryByText('AMD')).not.toBeInTheDocument();
    // 미매칭 섹터(미분류/ZZZ)는 숨김
    expect(screen.queryByText('ZZZ')).not.toBeInTheDocument();
  });

  it('카드 클릭 시 router.push(?symbol=...) 호출', () => {
    render(<MindmapTreeBoard />);
    fireEvent.click(screen.getByText('TECHNOLOGY'));
    fireEvent.click(screen.getByText('Semiconductors'));
    fireEvent.click(screen.getByRole('button', { name: 'NVDA 카드' }));
    expect(mockPush).toHaveBeenCalledWith('/chainsight/mindmap?symbol=NVDA');
  });

  it('?symbol=NVDA 있으면 상세 패널 렌더', () => {
    mockSymbolParam = 'NVDA';
    render(<MindmapTreeBoard />);
    expect(screen.getByTestId('mindmap-card-detail')).toBeInTheDocument();
  });

  it('로딩 상태 렌더', () => {
    treeResult = { data: undefined, isLoading: true, isError: false, refetch: vi.fn() };
    render(<MindmapTreeBoard />);
    expect(screen.getByText('마인드맵을 불러오는 중...')).toBeInTheDocument();
  });

  it('오류 상태: 재시도 버튼', () => {
    const refetch = vi.fn();
    treeResult = { data: undefined, isLoading: false, isError: true, refetch };
    render(<MindmapTreeBoard />);
    fireEvent.click(screen.getByText('다시 시도'));
    expect(refetch).toHaveBeenCalledTimes(1);
  });
});
