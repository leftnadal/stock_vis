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
    story: {
      threads: [
        {
          partner: 'AMD', partner_name: 'AMD Inc', count_7d: 5, count_90d: 40,
          weekly_avg_90d: 3.11, activity_ratio: 1.61,
          last_co_mention_date: '2026-08-27', days_since: 1, quiet: false,
        },
      ],
      thread_total: 1,
      threads_capped: false,
      shown: 1,
    },
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

  it('이 종목의 이야기: 활동 스레드 + "관계 아님" 캡션 + 게이지 수치', () => {
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText('이 종목의 이야기')).toBeInTheDocument();
    expect(screen.getByText(/관계 아님 · 동시 언급/)).toBeInTheDocument();
    expect(screen.getByText('AMD')).toBeInTheDocument();
    expect(screen.getByText('7일 5회')).toBeInTheDocument();
    expect(screen.getByText('주간평균 3.11')).toBeInTheDocument();
    expect(screen.getByText('어제')).toBeInTheDocument(); // days_since=1
  });

  it('threads_capped: "상위 N / 전체 M" 표기', () => {
    cardResult = {
      data: card({ story: { threads: [], thread_total: 172, threads_capped: true, shown: 10 } }),
      isLoading: false, isError: false, refetch: vi.fn(),
    };
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText('상위 10 / 전체 172')).toBeInTheDocument();
  });

  it('7일 활동 0(quiet) → 게이지 대신 "최근 조용함 · 마지막"', () => {
    cardResult = {
      data: card({
        story: {
          threads: [{
            partner: 'CCC', partner_name: 'CCC Co', count_7d: 0, count_90d: 8,
            weekly_avg_90d: 0.62, activity_ratio: null,
            last_co_mention_date: '2026-07-10', days_since: 49, quiet: true,
          }],
          thread_total: 1, threads_capped: false, shown: 1,
        },
      }),
      isLoading: false, isError: false, refetch: vi.fn(),
    };
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText(/최근 조용함 · 마지막 2026-07-10/)).toBeInTheDocument();
    expect(screen.queryByText(/7일/)).not.toBeInTheDocument();
  });

  it('그룹 0개 → "아직 관찰된 이야기 없음" 빈 상태', () => {
    cardResult = {
      data: card({ story: { threads: [], thread_total: 0, threads_capped: false, shown: 0 } }),
      isLoading: false, isError: false, refetch: vi.fn(),
    };
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    expect(screen.getByText('아직 관찰된 이야기 없음')).toBeInTheDocument();
  });

  it('이야기 스레드 클릭 → onSelectOther(partner) 호출', () => {
    render(<MindmapCardDetail symbol="NVDA" onSelectOther={onSelectOther} onClose={onClose} />);
    fireEvent.click(screen.getByText('AMD'));
    expect(onSelectOther).toHaveBeenCalledWith('AMD');
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
