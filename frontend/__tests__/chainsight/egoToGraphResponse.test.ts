import { describe, it, expect } from 'vitest';
import { egoToGraphResponse } from '@/components/chainsight/egoAdapter';
import type { EgoGraphResponse } from '@/types/chainsight';

// ⑳-3 S1: PG ego 응답 → 레거시 GraphResponse 어댑터 (GraphCanvas/GraphMiniView 공유)
function makeEgo(): EgoGraphResponse {
  return {
    center: { symbol: 'HAL', name: 'Halliburton Company' },
    nodes: [
      { symbol: 'HAL', name: 'Halliburton Company', sector: 'Energy' },
      { symbol: 'CTRA', name: 'Coterra Energy Inc.', sector: 'Energy' },
      { symbol: 'SLB', name: 'Schlumberger', sector: 'Energy' },
    ],
    edges: [
      {
        source: 'HAL', target: 'CTRA', relation_type: 'PEER_OF', truth_score: 85,
        evidence_count: 2, last_mentioned: '2026-07-01',
        trend: { direction: 'flat', delta: 0, points: [] },
        grade: 'confirmed', grade_source: 'market_peer', basis_summary: 'Peer 관계',
        last_observed_at: '2026-07-27',
      },
      {
        source: 'SLB', target: 'HAL', relation_type: 'COMPETES_WITH', truth_score: 85,
        evidence_count: 0, last_mentioned: null,
        trend: { direction: 'flat', delta: 0, points: [] },
        grade: 'confirmed', grade_source: 'sec_filing', basis_summary: '경쟁',
        last_observed_at: '2026-07-27',
      },
    ],
    meta: { total_edges: 2, returned: 2, filtered_by: { min_score: 0, types: null, limit: 50, trend_window: 12 } },
  };
}

describe('egoToGraphResponse', () => {
  it('center를 symbol→ticker로 매핑하고 sector는 nodes에서 조회', () => {
    const r = egoToGraphResponse(makeEgo());
    expect(r.center.ticker).toBe('HAL');
    expect(r.center.name).toBe('Halliburton Company');
    expect(r.center.sector).toBe('Energy');
  });

  it('center를 제외한 이웃만 nodes에 담고 symbol→ticker 매핑', () => {
    const r = egoToGraphResponse(makeEgo());
    const tickers = r.nodes.map((n) => n.ticker).sort();
    expect(tickers).toEqual(['CTRA', 'SLB']);
    expect(r.nodes.every((n) => n.ticker !== 'HAL')).toBe(true);
  });

  it('edges를 source→from, target→to, relation_type→type로 매핑(양방향 보존)', () => {
    const r = egoToGraphResponse(makeEgo());
    expect(r.edges).toEqual([
      { from: 'HAL', to: 'CTRA', type: 'PEER_OF' },
      { from: 'SLB', to: 'HAL', type: 'COMPETES_WITH' },
    ]);
  });

  it('meta.node_count=center+이웃, edge_count=엣지수', () => {
    const r = egoToGraphResponse(makeEgo());
    expect(r.meta.node_count).toBe(3); // HAL + CTRA + SLB
    expect(r.meta.edge_count).toBe(2);
    expect(r.meta.depth).toBe(1);
  });

  it('빈 ego(엣지 0)도 안전 — center만, nodes/edges 빈 배열', () => {
    const ego = makeEgo();
    ego.nodes = [{ symbol: 'HAL', name: 'Halliburton Company', sector: 'Energy' }];
    ego.edges = [];
    const r = egoToGraphResponse(ego);
    expect(r.nodes).toEqual([]);
    expect(r.edges).toEqual([]);
    expect(r.center.ticker).toBe('HAL');
    expect(r.meta.node_count).toBe(1);
  });
});
