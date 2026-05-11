import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import GraphCanvas from '@/components/chainsight/GraphCanvas';

// graphStyles mock
vi.mock('@/components/chainsight/graphStyles', () => ({
  getRelationStyle: (type: string) => ({
    color: '#999',
    label: type,
    width: 2,
    dash: undefined,
  }),
  getSectorColor: () => '#3B82F6',
  getNodeRadius: (isCenter: boolean) => (isCenter ? 32 : 14),
}));

function makeMockForceGraph() {
  const calls: Record<string, unknown[]> = {};
  const MockForceGraph = vi.fn((props: Record<string, unknown>) => {
    Object.entries(props).forEach(([k, v]) => {
      if (!calls[k]) calls[k] = [];
      calls[k].push(v);
    });
    return <div data-testid="force-graph" />;
  });
  return { MockForceGraph, calls };
}

const graphData = {
  center: { ticker: 'AAPL', name: 'Apple', sector: 'Technology', market_cap: 3e12, pagerank_score: 1 },
  nodes: [
    { ticker: 'MSFT', name: 'Microsoft', sector: 'Technology', market_cap: 2.8e12, pagerank_score: 0.8 },
    { ticker: 'GOOGL', name: 'Alphabet', sector: 'Technology', market_cap: 2e12, pagerank_score: 0.7 },
  ],
  edges: [
    { from: 'AAPL', to: 'MSFT', type: 'COMPETES_WITH' },
    { from: 'AAPL', to: 'GOOGL', type: 'PEER_OF' },
  ],
  meta: { depth: 1, node_count: 3, edge_count: 2, query_ms: 45 },
};

describe('GraphCanvas', () => {
  it('ForceGraph2D에 변환된 graphData를 전달한다', () => {
    const { MockForceGraph } = makeMockForceGraph();

    render(
      <GraphCanvas
        data={graphData}
        width={800}
        height={600}
        selectedNode={null}
        highlightRelTypes={[]}
        onNodeClick={vi.fn()}
        ForceGraph2D={MockForceGraph}
      />,
    );

    // ForceGraph2D가 호출됨
    expect(MockForceGraph).toHaveBeenCalled();
    const props = MockForceGraph.mock.calls[0][0] as Record<string, unknown>;

    // graphData 노드가 center + 2 neighbor = 3개
    const gd = props.graphData as { nodes: unknown[]; links: unknown[] };
    expect(gd.nodes).toHaveLength(3);
    expect(gd.links).toHaveLength(2);
  });

  it('onNodeClick이 ForceGraph2D의 onNodeClick을 통해 호출된다', () => {
    const onNodeClick = vi.fn();
    const MockForceGraph = vi.fn((props: Record<string, unknown>) => {
      // 시뮬레이트: ForceGraph2D가 노드 클릭 콜백 호출
      const handler = props.onNodeClick as (node: { ticker: string }) => void;
      handler({ ticker: 'MSFT' });
      return <div data-testid="force-graph" />;
    });

    render(
      <GraphCanvas
        data={graphData}
        width={800}
        height={600}
        selectedNode={null}
        highlightRelTypes={[]}
        onNodeClick={onNodeClick}
        ForceGraph2D={MockForceGraph}
      />,
    );

    expect(onNodeClick).toHaveBeenCalledWith('MSFT');
  });

  it('center가 없는 빈 데이터에서 빈 노드/링크를 전달한다', () => {
    const { MockForceGraph } = makeMockForceGraph();
    const emptyData = { center: undefined, nodes: [], edges: [], meta: { depth: 0, node_count: 0, edge_count: 0, query_ms: 0 } };

    render(
      <GraphCanvas
        data={emptyData as unknown as typeof graphData}
        width={800}
        height={600}
        selectedNode={null}
        highlightRelTypes={[]}
        onNodeClick={vi.fn()}
        ForceGraph2D={MockForceGraph}
      />,
    );

    const props = MockForceGraph.mock.calls[0][0] as Record<string, unknown>;
    const gd = props.graphData as { nodes: unknown[]; links: unknown[] };
    expect(gd.nodes).toHaveLength(0);
    expect(gd.links).toHaveLength(0);
  });
});
