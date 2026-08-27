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
    recent_new_connections_7d: 4,
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
              { ticker: 'NVDA', name: 'NVIDIA', gate_conn_count: 5, group_signal_count: 2, new_conn_7d: 3 },
              {
                ticker: 'AMD',
                name: 'Advanced Micro Devices',
                gate_conn_count: 0,
                group_signal_count: 0,
                new_conn_7d: 0,
              },
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
            cards: [
              { ticker: 'ZZZ', name: 'Zzz Corp', gate_conn_count: 1, group_signal_count: 0, new_conn_7d: 0 },
            ],
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
    expect(screen.queryByText('반도체')).not.toBeInTheDocument();
    expect(screen.queryByText('NVDA')).not.toBeInTheDocument();
  });

  it('sector 클릭 → industry 펼침 → industry 클릭 → 카드 그리드 렌더', () => {
    render(<MindmapTreeBoard />);
    fireEvent.click(screen.getByText('TECHNOLOGY'));
    expect(screen.getByText('반도체')).toBeInTheDocument();
    fireEvent.click(screen.getByText('반도체'));
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    expect(screen.getByText('연결 5')).toBeInTheDocument();
    expect(screen.getByText('그룹 2')).toBeInTheDocument();
  });

  it('검색어 입력 시 매칭 sector/industry만 자동 펼쳐짐', () => {
    render(<MindmapTreeBoard />);
    fireEvent.change(screen.getByLabelText('티커 또는 종목명 검색'), { target: { value: 'nvda' } });
    expect(screen.getByText('반도체')).toBeInTheDocument();
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    // 미매칭 카드(AMD)는 검색 중 숨김
    expect(screen.queryByText('AMD')).not.toBeInTheDocument();
    // 미매칭 섹터(미분류/ZZZ)는 숨김
    expect(screen.queryByText('ZZZ')).not.toBeInTheDocument();
  });

  it('카드 클릭 시 router.push(?symbol=...) 호출', () => {
    render(<MindmapTreeBoard />);
    fireEvent.click(screen.getByText('TECHNOLOGY'));
    fireEvent.click(screen.getByText('반도체'));
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

  // R1 Phase C-2: 관측성 배지 + 요약 스트립
  it('요약 스트립에 recent_new_connections_7d 표시', () => {
    render(<MindmapTreeBoard />);
    expect(screen.getByText('최근 7일 신규 연결 4건')).toBeInTheDocument();
  });

  it('recent_new_connections_7d=0이면 "없음" 문구', () => {
    treeResult = { data: { ...tree(), recent_new_connections_7d: 0 }, isLoading: false, isError: false, refetch: vi.fn() };
    render(<MindmapTreeBoard />);
    expect(screen.getByText('최근 7일 신규 연결 없음')).toBeInTheDocument();
  });

  it('new_conn_7d>0 카드에 신규 배지 표시, 0이면 미표시', () => {
    render(<MindmapTreeBoard />);
    fireEvent.click(screen.getByText('TECHNOLOGY'));
    fireEvent.click(screen.getByText('반도체'));
    expect(screen.getByText('新 +3')).toBeInTheDocument(); // NVDA
    expect(screen.queryByText(/新 \+0/)).not.toBeInTheDocument(); // AMD는 미표시
  });

  // R1 Phase C-1: 필터·정렬 (fixture: NVDA conn=5, AMD conn=0, ZZZ conn=1)
  it('필터 "연결 있음" → gate_conn_count=0 카드(AMD) 숨김 + 자동 펼침', () => {
    render(<MindmapTreeBoard />);
    fireEvent.click(screen.getByRole('button', { name: '연결 있음' }));
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    expect(screen.getByText('ZZZ')).toBeInTheDocument();
    expect(screen.queryByText('AMD')).not.toBeInTheDocument();
  });

  it('필터 "연결 없음" → gate_conn_count>0 카드(NVDA/ZZZ) 숨김, AMD만 노출', () => {
    render(<MindmapTreeBoard />);
    fireEvent.click(screen.getByRole('button', { name: '연결 없음' }));
    expect(screen.getByText('AMD')).toBeInTheDocument();
    expect(screen.queryByText('NVDA')).not.toBeInTheDocument();
    expect(screen.queryByText('ZZZ')).not.toBeInTheDocument();
  });

  it('정렬 "연결 적은순" 선택 시 카드 순서가 오름차순으로 재배열', () => {
    render(<MindmapTreeBoard />);
    fireEvent.click(screen.getByText('TECHNOLOGY'));
    fireEvent.click(screen.getByText('반도체'));
    fireEvent.change(screen.getByLabelText('카드 정렬'), { target: { value: 'conn_asc' } });
    const tickers = screen.getAllByText(/^(NVDA|AMD)$/).map((el) => el.textContent);
    expect(tickers).toEqual(['AMD', 'NVDA']); // AMD(0) → NVDA(5)
  });

  // R1 Phase C-3: sector 한글화(매핑 없으면 영문 원문 fallback)
  it('매핑된 sector는 한글 라벨로 표시(fallback 아닌 값)', () => {
    treeResult = {
      data: { ...tree(), sectors: [{ ...tree().sectors[0], sector: 'Technology' }] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    };
    render(<MindmapTreeBoard />);
    expect(screen.getByText('기술')).toBeInTheDocument();
  });
});
