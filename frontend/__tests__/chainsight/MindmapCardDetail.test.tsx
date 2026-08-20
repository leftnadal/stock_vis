/**
 * MindmapCardDetail (CS-P5-FE-CARD B4) — 확인된 연결 vs 같은 그룹 분리, ACQUIRED 빈 상태, 테마 placeholder.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { MindmapCardResponse } from '@/types/chainsight';

let cardResult: { data?: MindmapCardResponse; isLoading: boolean; isError: boolean; refetch: () => void };
vi.mock('@/hooks/useMindmap', () => ({
  useMindmapCard: () => cardResult,
}));

import MindmapCardDetail from '@/components/chainsight/MindmapCardDetail';

function card(partial: Partial<MindmapCardResponse> = {}): MindmapCardResponse {
  return {
    symbol: 'NVDA',
    name: 'NVIDIA',
    connection_count: 1,
    connections: [
      {
        other: 'TSM',
        other_name: 'Taiwan Semiconductor',
        relation_type: 'SUPPLIES_TO',
        direction: 'in',
        sync_strength: 0.82,
        contract_date: '2026-03-01',
        truth_score: 91,
        status: 'confirmed',
        basis: 'SEC 10-K',
      },
    ],
    acquired: [],
    groups: [{ other: 'AMD', other_name: 'AMD Inc', co_mention_count: 12 }],
    group_total: 1,
    group_capped: false,
    ...partial,
  };
}

const onSelectOther = vi.fn();
const onClose = vi.fn();

beforeEach(() => {
  onSelectOther.mockClear();
  onClose.mockClear();
  cardResult = { data: card(), isLoading: false, isError: false, refetch: vi.fn() };
});

describe('MindmapCardDetail (CS-P5-FE-CARD B4)', () => {
  it('확인된 연결: 상대·유형 한글 라벨·방향·동조·계약일 렌더', () => {
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText('TSM')).toBeInTheDocument();
    expect(screen.getByText('공급')).toBeInTheDocument();
    expect(screen.getByText('TSM →')).toBeInTheDocument(); // direction=in
    expect(screen.getByText(/동조 0.82/)).toBeInTheDocument();
    expect(screen.getByText(/계약일 2026-03-01/)).toBeInTheDocument();
  });

  it('같은 그룹은 연결과 분리 + "관계 아님" 캡션', () => {
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText(/관계 아님 · 동시 언급/)).toBeInTheDocument();
    expect(screen.getByText(/AMD/)).toBeInTheDocument();
  });

  it('group_capped: "상위 20 / 전체 N" 표기', () => {
    cardResult = {
      data: card({ group_capped: true, group_total: 172 }),
      isLoading: false, isError: false, refetch: vi.fn(),
    };
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText('상위 20 / 전체 172')).toBeInTheDocument();
  });

  it('ACQUIRED 빈 배열 → "인수 관계 없음" 빈 상태(구조는 항상 렌더)', () => {
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText('인수·피인수')).toBeInTheDocument();
    expect(screen.getByText('인수 관계 없음')).toBeInTheDocument();
  });

  it('ACQUIRED 데이터 존재 시 역할 라벨(→인수/←피인수) 렌더', () => {
    cardResult = {
      data: card({ acquired: [{ other: 'MLNX', other_name: 'Mellanox', role: 'acquirer' }] }),
      isLoading: false, isError: false, refetch: vi.fn(),
    };
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText('→ 인수')).toBeInTheDocument();
  });

  it('테마 슬롯 placeholder 렌더(준비 중)', () => {
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText('테마 (준비 중)')).toBeInTheDocument();
  });

  it('연결 클릭 → onSelectOther(other) 호출', () => {
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    fireEvent.click(screen.getByText('TSM'));
    expect(onSelectOther).toHaveBeenCalledWith('TSM');
  });

  it('닫기 버튼 → onClose 호출', () => {
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText('상세 패널 닫기'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('로딩 상태 렌더', () => {
    cardResult = { data: undefined, isLoading: true, isError: false, refetch: vi.fn() };
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText('카드를 불러오는 중...')).toBeInTheDocument();
  });

  it('오류 상태: 다시 시도 버튼', () => {
    const refetch = vi.fn();
    cardResult = { data: undefined, isLoading: false, isError: true, refetch };
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    fireEvent.click(screen.getByText('다시 시도'));
    expect(refetch).toHaveBeenCalledTimes(1);
  });
});
