import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BackboneGraph, { edgeKey } from '@/components/chainsight/BackboneGraph';
import type { BackboneSymbol, BackboneEdge } from '@/types/backbone';

const topSymbols: BackboneSymbol[] = [
  { symbol: 'A', pagerank: 0.5, degree: 3 },
  { symbol: 'B', pagerank: 0.3, degree: 2 },
  { symbol: 'C', pagerank: 0.2, degree: 1 },
];

function edge(a: string, b: string, score: number): BackboneEdge {
  return {
    symbol_a: a, symbol_b: b, score,
    category: 'truth', evidence_count: 2, observed_count: 1, trust: 'confirmed',
  };
}

function mockFG() {
  const MockForceGraph = vi.fn((props: Record<string, unknown>) => {
    void props; // 타입 확보용(mock.calls[0][0]) — 참조로 unused 경고 제거
    return <div data-testid="force-graph" />;
  });
  return MockForceGraph;
}

const baseProps = {
  topSymbols,
  theta: 0.85,
  width: 700,
  height: 400,
  selectedEdgeKey: null,
  onEdgeSelect: vi.fn(),
};

describe('BackboneGraph', () => {
  it('top 심볼을 노드로, 유도 부분그래프 엣지를 링크로 변환한다', () => {
    const MockForceGraph = mockFG();
    render(
      <BackboneGraph
        {...baseProps}
        edges={[edge('A', 'B', 0.9), edge('B', 'C', 0.9), edge('A', 'Z', 0.9)]}
        ForceGraph2D={MockForceGraph}
      />,
    );
    const props = MockForceGraph.mock.calls[0][0] as Record<string, unknown>;
    const gd = props.graphData as { nodes: unknown[]; links: unknown[] };
    expect(gd.nodes).toHaveLength(3);
    // A-Z 는 Z 가 top 심볼이 아니므로 제외 → 링크 2개
    expect(gd.links).toHaveLength(2);
  });

  it('θ 기준 실선(≥)·점선(<) dash 를 부여한다', () => {
    const MockForceGraph = mockFG();
    render(
      <BackboneGraph
        {...baseProps}
        edges={[edge('A', 'B', 0.90), edge('B', 'C', 0.80)]}
        ForceGraph2D={MockForceGraph}
      />,
    );
    const props = MockForceGraph.mock.calls[0][0] as Record<string, unknown>;
    const links = (props.graphData as { links: { dash?: number[] }[] }).links;
    const ab = links.find((l) => (l as { edge: BackboneEdge }).edge.symbol_a === 'A')!;
    const bc = links.find((l) => (l as { edge: BackboneEdge }).edge.symbol_a === 'B')!;
    expect(ab.dash).toBeUndefined();          // 0.90 ≥ θ = 실선
    expect(bc.dash).toEqual([4, 4]);          // 0.80 < θ = 점선
  });

  it('onLinkClick 이 원 엣지로 onEdgeSelect 를 호출한다', () => {
    const onEdgeSelect = vi.fn();
    const MockForceGraph = vi.fn((props: Record<string, unknown>) => {
      const gd = props.graphData as { links: { edge: BackboneEdge }[] };
      const handler = props.onLinkClick as (l: unknown) => void;
      handler(gd.links[0]);
      return <div data-testid="force-graph" />;
    });
    render(
      <BackboneGraph
        {...baseProps}
        onEdgeSelect={onEdgeSelect}
        edges={[edge('A', 'B', 0.9)]}
        ForceGraph2D={MockForceGraph}
      />,
    );
    expect(onEdgeSelect).toHaveBeenCalledTimes(1);
    expect(onEdgeSelect.mock.calls[0][0]).toMatchObject({ symbol_a: 'A', symbol_b: 'B' });
  });

  it('edgeKey 는 무향 정규화(정렬)한다', () => {
    expect(edgeKey({ symbol_a: 'B', symbol_b: 'A' })).toBe('A|B');
    expect(edgeKey({ symbol_a: 'A', symbol_b: 'B' })).toBe('A|B');
  });
});
