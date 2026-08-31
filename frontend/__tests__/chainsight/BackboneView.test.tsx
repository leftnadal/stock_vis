import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import BackboneView from '@/components/chainsight/BackboneView';
import { useBackbone } from '@/hooks/useBackbone';
import type { BackboneResponse } from '@/types/backbone';

vi.mock('@/hooks/useBackbone');
const mockUseBackbone = vi.mocked(useBackbone);

const RESP: BackboneResponse = {
  as_of: '2026-08-31',
  computed_at: '2026-08-31T08:00:00Z',
  graph_size: { nodes: 3, edges: 2 },
  theta: 0.85,
  top_symbols: [
    { symbol: 'ORCL', pagerank: 0.006, degree: 32 },
    { symbol: 'NVDA', pagerank: 0.005, degree: 31 },
    { symbol: 'AMD', pagerank: 0.004, degree: 28 },
  ],
  edges: [
    { symbol_a: 'ORCL', symbol_b: 'NVDA', score: 0.9, category: 'truth',
      evidence_count: 5, observed_count: 3, trust: 'confirmed' },
    { symbol_a: 'NVDA', symbol_b: 'AMD', score: 0.85, category: 'market',
      evidence_count: 1, observed_count: 0, trust: 'confirmed' },
  ],
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mockResult(over: Partial<any>) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return { data: undefined, isLoading: false, isError: false, ...over } as any;
}

const MockFG = vi.fn(() => <div data-testid="force-graph" />);

beforeEach(() => {
  MockFG.mockClear();
});

describe('BackboneView', () => {
  it('중심성 top-N 리스트와 그래프를 렌더한다', () => {
    mockUseBackbone.mockReturnValue(mockResult({ data: RESP }));
    render(<BackboneView ForceGraph2D={MockFG} />);
    expect(screen.getByTestId('backbone-toplist')).toBeInTheDocument();
    expect(screen.getByText('ORCL')).toBeInTheDocument();
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    expect(screen.getByTestId('backbone-graph')).toBeInTheDocument();
  });

  it('빈 데이터에서 empty 상태를 렌더한다', () => {
    mockUseBackbone.mockReturnValue(
      mockResult({ data: { ...RESP, top_symbols: [], edges: [], graph_size: { nodes: 0, edges: 0 } } }),
    );
    render(<BackboneView ForceGraph2D={MockFG} />);
    expect(screen.getByTestId('backbone-empty')).toBeInTheDocument();
    expect(screen.queryByTestId('backbone-graph')).not.toBeInTheDocument();
  });

  it('로드 에러 상태를 렌더한다', () => {
    mockUseBackbone.mockReturnValue(mockResult({ isError: true }));
    render(<BackboneView ForceGraph2D={MockFG} />);
    expect(screen.getByText(/불러오지 못했습니다/)).toBeInTheDocument();
  });

  it('엣지 선택 시 근거 바를 표시한다', () => {
    mockUseBackbone.mockReturnValue(mockResult({ data: RESP }));
    // 그래프 마운트 시 첫 링크를 클릭하도록 mock ForceGraph 를 구성.
    const ClickingFG = vi.fn((props: Record<string, unknown>) => {
      const gd = props.graphData as { links: { edge: unknown }[] };
      const handler = props.onLinkClick as (l: unknown) => void;
      if (gd?.links?.length) handler(gd.links[0]);
      return <div data-testid="force-graph" />;
    });
    render(<BackboneView ForceGraph2D={ClickingFG} />);
    const bar = screen.getByTestId('backbone-evidence-bar');
    expect(bar).toBeInTheDocument();
    expect(bar).toHaveTextContent('ORCL');
    expect(bar).toHaveTextContent('NVDA');
    expect(bar).toHaveTextContent('0.90');   // score
    expect(bar).toHaveTextContent('확정');    // trust badge (confirmed)
  });

  it('선택 전에는 근거 바가 없다', () => {
    mockUseBackbone.mockReturnValue(mockResult({ data: RESP }));
    render(<BackboneView ForceGraph2D={MockFG} />);
    expect(screen.queryByTestId('backbone-evidence-bar')).not.toBeInTheDocument();
  });
});
