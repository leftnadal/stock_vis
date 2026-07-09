import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { NewsStrip } from '@/components/strip/NewsStrip';
import { useNewsStrip } from '@/hooks/useNewsStrip';
import type { NewsStripItem } from '@/services/stripService';

vi.mock('@/hooks/useNewsStrip', () => ({ useNewsStrip: vi.fn() }));

const mockUse = vi.mocked(useNewsStrip);

function item(overrides: Partial<NewsStripItem>): NewsStripItem {
  return {
    headline: '헤드라인',
    symbols: ['AAA'],
    direction: 'up',
    tier: 3,
    relevance_line: '관심 종목 관련',
    collapsed_count: 0,
    badge: null,
    published_at: '2026-07-09T00:00:00Z',
    article_url: 'http://n/1',
    ...overrides,
  };
}

function mockResult(partial: any) {
  mockUse.mockReturnValue(partial as ReturnType<typeof useNewsStrip>);
}

describe('NewsStrip', () => {
  beforeEach(() => vi.clearAllMocks());

  it('실패 격리: isError면 아무것도 렌더 안 함(null)', () => {
    mockResult({ isError: true, data: undefined });
    const { container } = render(<NewsStrip />);
    expect(container.firstChild).toBeNull();
  });

  it('빈 응답(items 0)이면 비표시', () => {
    mockResult({ isError: false, data: { as_of: 'x', theta: 0, items: [] } });
    const { container } = render(<NewsStrip />);
    expect(container.firstChild).toBeNull();
  });

  it('데이터 미도착(undefined)이면 비표시', () => {
    mockResult({ isError: false, data: undefined });
    const { container } = render(<NewsStrip />);
    expect(container.firstChild).toBeNull();
  });

  it('칩을 렌더한다(상한 5)', () => {
    const items = Array.from({ length: 5 }, (_, i) =>
      item({ headline: `뉴스${i}`, article_url: `http://n/${i}` }),
    );
    mockResult({ isError: false, data: { as_of: 'x', theta: 60, items } });
    render(<NewsStrip />);
    expect(screen.getAllByRole('listitem')).toHaveLength(5);
    expect(screen.getByText('뉴스0')).toBeInTheDocument();
  });

  it('접기 표기 "+n건"을 렌더한다', () => {
    mockResult({
      isError: false,
      data: { as_of: 'x', theta: 60, items: [item({ collapsed_count: 3 })] },
    });
    render(<NewsStrip />);
    expect(screen.getByText('+3건')).toBeInTheDocument();
  });

  it('관계망 배지를 렌더한다', () => {
    mockResult({
      isError: false,
      data: {
        as_of: 'x',
        theta: 60,
        items: [item({ badge: { pair: 'AAA↔BBB', confidence: 80 } })],
      },
    });
    render(<NewsStrip />);
    expect(screen.getByText(/AAA↔BBB/)).toBeInTheDocument();
  });
});
