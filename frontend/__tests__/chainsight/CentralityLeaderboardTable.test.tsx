import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import CentralityLeaderboardTable from '@/components/chainsight/CentralityLeaderboardTable';
import type { CentralityLeaderboardItem } from '@/types/chainsight';

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: ReactNode;
    [k: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

function item(over: Partial<CentralityLeaderboardItem>): CentralityLeaderboardItem {
  return {
    symbol: 'NVDA',
    name: 'NVIDIA',
    pagerank: 0.0088,
    betweenness: 0.33,
    pagerank_rank: 1,
    betweenness_rank: 1,
    graph_nodes: 555,
    graph_edges: 9551,
    rank: 1,
    rank_delta: null,
    ...over,
  };
}

describe('CentralityLeaderboardTable', () => {
  it('심볼·이름·지표값 렌더', () => {
    render(
      <CentralityLeaderboardTable
        items={[item({ symbol: 'NVDA', name: 'NVIDIA', pagerank: 0.0088 })]}
        metricKey="pagerank"
      />,
    );
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    expect(screen.getByText('NVIDIA')).toBeInTheDocument();
    expect(screen.getByText('0.0088')).toBeInTheDocument(); // pagerank 포맷
  });

  it('rank_delta 상승(양수) → ▲ + 강세색(up)', () => {
    render(
      <CentralityLeaderboardTable
        items={[item({ symbol: 'AAA', rank_delta: 3 })]}
        metricKey="pagerank"
      />,
    );
    const delta = screen.getByTestId('rank-delta');
    expect(delta).toHaveAttribute('data-state', 'up');
    expect(delta.textContent).toContain('▲');
    expect(delta.textContent).toContain('3');
    expect(delta.className).toMatch(/rose/);
  });

  it('rank_delta 하락(음수) → ▼ + 약세색(down), 절대값 표시', () => {
    render(
      <CentralityLeaderboardTable
        items={[item({ symbol: 'BBB', rank_delta: -2 })]}
        metricKey="pagerank"
      />,
    );
    const delta = screen.getByTestId('rank-delta');
    expect(delta).toHaveAttribute('data-state', 'down');
    expect(delta.textContent).toContain('▼');
    expect(delta.textContent).toContain('2'); // 절대값
    expect(delta.className).toMatch(/sky/);
  });

  it('rank_delta 0 → — (중립)', () => {
    render(
      <CentralityLeaderboardTable
        items={[item({ symbol: 'CCC', rank_delta: 0 })]}
        metricKey="pagerank"
      />,
    );
    const delta = screen.getByTestId('rank-delta');
    expect(delta).toHaveAttribute('data-state', 'flat');
    expect(delta.textContent).toContain('—');
  });

  it('rank_delta null → NEW (전일 데이터 부재, 0과 의미 분리) (⑳-2 S5)', () => {
    render(
      <CentralityLeaderboardTable
        items={[item({ symbol: 'DDD', rank_delta: null })]}
        metricKey="pagerank"
      />,
    );
    const delta = screen.getByTestId('rank-delta');
    expect(delta).toHaveAttribute('data-state', 'new');
    expect(delta.textContent).toContain('NEW');
    expect(delta.textContent).not.toContain('—');
  });

  it('ego 링크 URL = /chainsight/market-graph?focus=SYMBOL', () => {
    render(
      <CentralityLeaderboardTable
        items={[item({ symbol: 'NVDA' })]}
        metricKey="pagerank"
      />,
    );
    const links = screen.getAllByRole('link', { name: /NVDA|관계망/ });
    expect(links.length).toBeGreaterThan(0);
    for (const l of links) {
      expect(l).toHaveAttribute(
        'href',
        '/chainsight/market-graph?focus=NVDA',
      );
    }
  });

  it('metric=betweenness → betweenness 값으로 포맷', () => {
    render(
      <CentralityLeaderboardTable
        items={[item({ symbol: 'X', betweenness: 0.3301 })]}
        metricKey="betweenness"
      />,
    );
    expect(screen.getByText('0.3301')).toBeInTheDocument();
  });

  it('빈 items → 안내 문구', () => {
    render(<CentralityLeaderboardTable items={[]} metricKey="pagerank" />);
    expect(screen.getByText(/데이터가 없습니다/)).toBeInTheDocument();
  });
});
