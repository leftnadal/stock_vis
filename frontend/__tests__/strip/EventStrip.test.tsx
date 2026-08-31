// 홈 이벤트 스트립(Screen S) — 실패 격리(null) · 빈 응답(null) · 카드 날짜순 · 티저 상한 2.
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { EventStrip } from '@/components/strip/EventStrip';
import { useEventStrip } from '@/hooks/useEventCalendar';
import type { EventItem, EventStripResponse } from '@/types/eventCalendar';

vi.mock('@/hooks/useEventCalendar', () => ({ useEventStrip: vi.fn() }));

const mockUse = vi.mocked(useEventStrip);

function item(overrides: Partial<EventItem>): EventItem {
  return {
    kind: 'macro',
    symbol: null,
    title: '거시 지표',
    event_date_et: '2026-09-11',
    event_time_et: null,
    session: null,
    event_dt_kst: null,
    d_day: 11,
    badges: [],
    detail: {},
    surprise: null,
    date_trust: null,
    date_observed_count: null,
    sources: [],
    status: 'scheduled',
    ...overrides,
  };
}

function mockResult(partial: Partial<{ isError: boolean; data: EventStripResponse | undefined }>) {
  mockUse.mockReturnValue(partial as ReturnType<typeof useEventStrip>);
}

describe('EventStrip', () => {
  beforeEach(() => vi.clearAllMocks());

  it('실패 격리: isError면 아무것도 렌더 안 함(null)', () => {
    mockResult({ isError: true, data: undefined });
    const { container } = render(<EventStrip />);
    expect(container.firstChild).toBeNull();
  });

  it('빈 응답(items 0)이면 비표시', () => {
    mockResult({ isError: false, data: { as_of: 'x', window_days: 45, items: [] } });
    const { container } = render(<EventStrip />);
    expect(container.firstChild).toBeNull();
  });

  it('데이터 미도착(undefined)이면 비표시', () => {
    mockResult({ isError: false, data: undefined });
    const { container } = render(<EventStrip />);
    expect(container.firstChild).toBeNull();
  });

  it('카드를 날짜 오름차순으로 렌더한다', () => {
    const items = [
      item({ kind: 'macro', symbol: null, title: 'CPI', event_date_et: '2026-09-11', d_day: 11 }),
      item({ kind: 'holiday', symbol: null, title: 'NYSE 휴장', event_date_et: '2026-09-01', d_day: 1 }),
      item({ kind: 'macro', symbol: null, title: 'ISM PMI', event_date_et: '2026-09-02', d_day: 2 }),
    ];
    mockResult({ isError: false, data: { as_of: 'x', window_days: 45, items } });
    render(<EventStrip />);

    const cards = screen.getAllByRole('listitem');
    expect(cards).toHaveLength(3);
    expect(cards[0]).toHaveTextContent('NYSE 휴장');
    expect(cards[1]).toHaveTextContent('ISM PMI');
    expect(cards[2]).toHaveTextContent('CPI');
  });

  it('관심 어닝 티저는 최대 2장만 렌더한다', () => {
    const items = [
      item({ kind: 'earnings', symbol: 'AVGO', title: 'AVGO 어닝', event_date_et: '2026-09-04', d_day: 4, sources: ['monitor'] }),
      item({ kind: 'earnings', symbol: 'TSM', title: 'TSM 어닝', event_date_et: '2026-09-05', d_day: 5, sources: ['watchlist'] }),
      item({ kind: 'earnings', symbol: 'NVDA', title: 'NVDA 어닝', event_date_et: '2026-09-06', d_day: 6, sources: ['monitor'] }),
      item({ kind: 'macro', symbol: null, title: 'CPI', event_date_et: '2026-09-11', d_day: 11 }),
    ];
    mockResult({ isError: false, data: { as_of: 'x', window_days: 45, items } });
    render(<EventStrip />);

    const cards = screen.getAllByRole('listitem');
    // earnings 3건 중 2건만 + macro 1건 = 3장.
    expect(cards).toHaveLength(3);
    expect(screen.getByText('AVGO 어닝')).toBeInTheDocument();
    expect(screen.getByText('TSM 어닝')).toBeInTheDocument();
    expect(screen.queryByText('NVDA 어닝')).not.toBeInTheDocument();
    expect(screen.getByText('CPI')).toBeInTheDocument();
  });
});
