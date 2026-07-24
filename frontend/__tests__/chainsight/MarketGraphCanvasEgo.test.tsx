/**
 * MarketGraphCanvas Ego 모드 테스트
 *
 * 범위: ego API 데이터 소스 전환 및 시각 인코딩 검증
 *  ⑴ ego 응답 렌더 — 노드/엣지 개수
 *  ⑵ 빈 이웃 상태
 *  ⑶ limit 절단 표시 (meta.returned < meta.total_edges)
 *  ⑷ truth_score/trend 시각 인코딩 헬퍼 반영
 */

import { describe, it, expect } from 'vitest';
import type { EgoGraphResponse } from '@/types/chainsight';
import {
  egoToNeighborShape,
  egoTruthScoreToWidth,
  egoTrendToColor,
} from '@/components/chainsight/egoAdapter';

// ── 픽스처 ──

function makeEgoResponse(overrides: Partial<EgoGraphResponse> = {}): EgoGraphResponse {
  return {
    center: { symbol: 'AAPL', name: 'Apple Inc.' },
    nodes: [
      { symbol: 'MSFT', name: 'Microsoft', sector: 'Technology' },
      { symbol: 'GOOGL', name: 'Alphabet', sector: 'Technology' },
    ],
    edges: [
      {
        source: 'AAPL',
        target: 'MSFT',
        relation_type: 'PEER_OF',
        truth_score: 80,
        evidence_count: 5,
        last_mentioned: '2026-07-19',
        trend: { direction: 'up', delta: 30, points: [{ period: '2026-07-01', score: 50 }] },
        grade: 'confirmed',
        grade_source: 'market_peer',
        basis_summary: 'Peer 관계 + 같은 산업',
        last_observed_at: '2026-07-19',
      },
      {
        source: 'AAPL',
        target: 'GOOGL',
        relation_type: 'COMPETES_WITH',
        truth_score: 60,
        evidence_count: 0,
        last_mentioned: null,
        trend: { direction: 'flat', delta: 0, points: [] },
        grade: 'likely',
        grade_source: 'sec_filing',
        basis_summary: 'SEC 10-K: compete',
        last_observed_at: null,
      },
    ],
    meta: {
      total_edges: 2,
      returned: 2,
      filtered_by: { min_score: 0, types: null, limit: 50, trend_window: 12 },
    },
    ...overrides,
  };
}

// ── 어댑터 테스트 ──

describe('egoToNeighborShape', () => {
  it('⑴ ego 응답을 neighbor 형태로 변환한다 — 노드/엣지 개수', () => {
    const ego = makeEgoResponse();
    const result = egoToNeighborShape(ego);

    // center는 별도 객체
    expect(result.center.symbol).toBe('AAPL');
    expect(result.center.name).toBe('Apple Inc.');

    // neighbors = edges 수만큼
    expect(result.neighbors).toHaveLength(2);
    expect(result.neighbors[0].symbol).toBe('MSFT');
    expect(result.neighbors[1].symbol).toBe('GOOGL');
  });

  it('⑴ 각 neighbor에 relation 정보가 올바르게 매핑된다', () => {
    const ego = makeEgoResponse();
    const result = egoToNeighborShape(ego);

    const msft = result.neighbors.find((n) => n.symbol === 'MSFT')!;
    expect(msft.relation.type).toBe('PEER_OF');
    expect(msft.relation.truth_score).toBe(80);
    expect(msft.relation.direction).toBe('outbound'); // source=AAPL=center → outbound
  });

  it('⑴ EgoNode에서 sector를 조회하여 neighbor에 반영한다', () => {
    const ego = makeEgoResponse();
    const result = egoToNeighborShape(ego);

    const msft = result.neighbors.find((n) => n.symbol === 'MSFT')!;
    expect(msft.sector).toBe('Technology');
  });

  it('⑵ 빈 이웃 상태 — edges=[] 이면 neighbors=[], cross_edges=[]', () => {
    const ego = makeEgoResponse({ edges: [], nodes: [] });
    const result = egoToNeighborShape(ego);

    expect(result.neighbors).toHaveLength(0);
    expect(result.cross_edges).toHaveLength(0);
  });

  it('ego는 2-hop 미제공 — cross_edges가 항상 빈 배열', () => {
    const ego = makeEgoResponse();
    const result = egoToNeighborShape(ego);

    expect(result.cross_edges).toEqual([]);
  });

  it('ego는 seed 정보 미제공 — seed_reasons가 빈 배열, seed_type=null', () => {
    const ego = makeEgoResponse();
    const result = egoToNeighborShape(ego);

    expect(result.center.seed_reasons).toEqual([]);
    expect(result.center.seed_type).toBeNull();
    for (const nb of result.neighbors) {
      expect(nb.seed_reasons).toEqual([]);
      expect(nb.seed_type).toBeNull();
    }
  });

  it('⑷ trend direction이 relation._ego_trend_direction으로 전달된다', () => {
    const ego = makeEgoResponse();
    const result = egoToNeighborShape(ego);

    const msft = result.neighbors.find((n) => n.symbol === 'MSFT')!;
    expect((msft.relation as any)._ego_trend_direction).toBe('up');

    const googl = result.neighbors.find((n) => n.symbol === 'GOOGL')!;
    expect((googl.relation as any)._ego_trend_direction).toBe('flat');
  });

  it('⑶ limit 절단: meta.returned < meta.total_edges일 때 반환 엣지 수는 returned와 일치', () => {
    // 백엔드가 50 limit로 96개 중 50개를 반환하는 케이스 시뮬레이션
    // egoToNeighborShape는 받은 edges만 처리하므로 반환 neighbors 수 = edges.length
    const limitedEdges = Array.from({ length: 3 }, (_, i) => ({
      source: 'AAPL',
      target: `SYM${i}`,
      relation_type: 'PEER_OF',
      truth_score: 50,
      evidence_count: 0,
      last_mentioned: null,
      trend: { direction: 'flat' as const, delta: 0, points: [] },
      grade: 'observed' as const,
      grade_source: 'market_peer' as const,
      basis_summary: '',
      last_observed_at: null,
    }));
    const ego = makeEgoResponse({
      edges: limitedEdges,
      nodes: limitedEdges.map((e) => ({ symbol: e.target, name: e.target, sector: 'Tech' })),
      meta: {
        total_edges: 96,
        returned: 3,
        filtered_by: { min_score: 0, types: null, limit: 3, trend_window: 12 },
      },
    });

    const result = egoToNeighborShape(ego);
    // returned(3) == neighbors.length, total_edges(96) > returned(3) → 절단 상태
    expect(result.neighbors).toHaveLength(ego.meta.returned);
    expect(ego.meta.total_edges).toBeGreaterThan(ego.meta.returned);
  });
});

// ── 시각 인코딩 헬퍼 테스트 ──

describe('egoTruthScoreToWidth', () => {
  it('⑷ score=0 → 최소 굵기 1px', () => {
    expect(egoTruthScoreToWidth(0)).toBe(1);
  });

  it('⑷ score=100 → 최대 굵기 4px', () => {
    expect(egoTruthScoreToWidth(100)).toBe(4);
  });

  it('⑷ score=50 → 중간 굵기 2.5px', () => {
    expect(egoTruthScoreToWidth(50)).toBeCloseTo(2.5);
  });

  it('⑷ score=80 → 1 + 0.8*3 = 3.4px', () => {
    expect(egoTruthScoreToWidth(80)).toBeCloseTo(3.4);
  });

  it('범위 초과값 clamp — score > 100 → 4px', () => {
    expect(egoTruthScoreToWidth(150)).toBe(4);
  });

  it('범위 초과값 clamp — score < 0 → 1px', () => {
    expect(egoTruthScoreToWidth(-10)).toBe(1);
  });
});

describe('egoTrendToColor', () => {
  it('⑷ up → green-500 (#22C55E)', () => {
    expect(egoTrendToColor('up')).toBe('#22C55E');
  });

  it('⑷ down → red-500 (#EF4444)', () => {
    expect(egoTrendToColor('down')).toBe('#EF4444');
  });

  it('⑷ flat → null (기본색 유지)', () => {
    expect(egoTrendToColor('flat')).toBeNull();
  });
});
