import { describe, it, expect } from 'vitest';
import { egoToMindmap } from '@/components/chainsight/egoMindmap';
import type { EgoGraphResponse, EgoEdge } from '@/types/chainsight';

// ⑳-3 S3-MINDMAP S4 — egoToMindmap 3층 그룹핑
function edge(partial: Partial<EgoEdge> & { target: string; relation_type: string }): EgoEdge {
  return {
    source: 'CTR',
    truth_score: 50,
    evidence_count: 0,
    last_mentioned: null,
    trend: { direction: 'flat', delta: 0, points: [] },
    grade: 'observed',
    grade_source: 'unknown',
    basis_summary: '',
    last_observed_at: null,
    ...partial,
  } as EgoEdge;
}

// NVDA형: SEC 태그 + 무태그 SEC + peer + 동종산업 + co_mention + price(제외)
function nvdaLike(): EgoGraphResponse {
  return {
    center: { symbol: 'CTR', name: 'Center' },
    nodes: [
      { symbol: 'CTR', name: 'Center', sector: 'Tech', industry_bucket: '반도체·메모리' },
      { symbol: 'SUP', name: 'Sup', sector: 'Tech', industry_bucket: '반도체·메모리' },
      { symbol: 'DEP', name: 'Dep', sector: 'Tech', industry_bucket: '클라우드·엔터프라이즈SW' },
      { symbol: 'PR1', name: 'Peer1', sector: 'Tech', industry_bucket: '반도체·메모리' },
      { symbol: 'PR2', name: 'Peer2', sector: 'Tech', industry_bucket: '클라우드·엔터프라이즈SW' },
      { symbol: 'IND', name: 'Ind', sector: 'Tech', industry_bucket: '반도체·메모리' },
      { symbol: 'NWS', name: 'News', sector: 'Tech', industry_bucket: null },
      { symbol: 'PRC', name: 'Price', sector: 'Tech', industry_bucket: '반도체·메모리' },
    ],
    edges: [
      edge({ target: 'SUP', relation_type: 'SUPPLIES_TO', relation_domain: '반도체·메모리', truth_score: 90 }),
      edge({ target: 'DEP', relation_type: 'DEPENDS_ON', truth_score: 70 }), // 무태그 SEC
      edge({ target: 'PR1', relation_type: 'PEER_OF', has_peer_source: true, truth_score: 80 }),
      edge({ target: 'PR2', relation_type: 'PEER_OF', has_peer_source: true, truth_score: 60 }),
      edge({ target: 'IND', relation_type: 'PEER_OF', has_industry_source: true, truth_score: 55 }),
      edge({ target: 'NWS', relation_type: 'CO_MENTIONED', truth_score: 0 }),
      edge({ target: 'PRC', relation_type: 'PRICE_CORRELATED', truth_score: 40 }), // 제외
    ],
    meta: { total_edges: 7, returned: 7, filtered_by: { min_score: 0, types: null, limit: 200, trend_window: 30 } },
  };
}

describe('egoToMindmap', () => {
  it('PRICE_CORRELATED는 제외하고 건수만 보고', () => {
    const mm = egoToMindmap(nvdaLike());
    expect(mm.excludedPriceCorrelated).toBe(1);
    const allTargets = mm.branches.flatMap((b) => [
      ...b.leaves.map((l) => l.symbol),
      ...b.subgroups.flatMap((s) => s.leaves.map((l) => l.symbol)),
    ]);
    expect(allTargets).not.toContain('PRC');
  });

  it('L1: relation_domain 태그 → SEC 도메인 가지', () => {
    const mm = egoToMindmap(nvdaLike());
    const dom = mm.branches.find((b) => b.kind === 'sec_domain');
    expect(dom?.label).toBe('반도체·메모리');
    expect(dom?.isSec).toBe(true);
    expect(dom?.leaves.map((l) => l.symbol)).toEqual(['SUP']);
  });

  it('L1 폴백: 무태그 SEC → 유형 수납 가지', () => {
    const mm = egoToMindmap(nvdaLike());
    const untagged = mm.branches.find((b) => b.kind === 'sec_untagged');
    expect(untagged?.label).toBe('의존 관계'); // DEPENDS_ON
    expect(untagged?.leaves.map((l) => l.symbol)).toEqual(['DEP']);
  });

  it('L2: peer는 industry 하위 그룹으로 분해', () => {
    const mm = egoToMindmap(nvdaLike());
    const peer = mm.branches.find((b) => b.kind === 'peer');
    expect(peer?.label).toBe('경쟁·Peer 기업');
    expect(peer?.count).toBe(2); // PR1, PR2
    const subLabels = peer?.subgroups.map((s) => s.label).sort();
    expect(subLabels).toEqual(['반도체·메모리', '클라우드·엔터프라이즈SW']);
  });

  it('L2: has_industry_source는 동종 산업 가지로 분리', () => {
    const mm = egoToMindmap(nvdaLike());
    const ind = mm.branches.find((b) => b.kind === 'industry');
    expect(ind?.label).toBe('동종 산업');
    expect(ind?.subgroups[0].leaves.map((l) => l.symbol)).toEqual(['IND']);
  });

  it('L3: CO_MENTIONED → 뉴스 동반언급 단일 가지', () => {
    const mm = egoToMindmap(nvdaLike());
    const news = mm.branches.find((b) => b.kind === 'co_mention');
    expect(news?.label).toBe('뉴스 동반언급');
    expect(news?.leaves.map((l) => l.symbol)).toEqual(['NWS']);
  });

  it('SEC 가지가 시장 가지보다 먼저 정렬', () => {
    const mm = egoToMindmap(nvdaLike());
    const firstMarketIdx = mm.branches.findIndex((b) => !b.isSec);
    const lastSecIdx = mm.branches.map((b) => b.isSec).lastIndexOf(true);
    expect(lastSecIdx).toBeLessThan(firstMarketIdx);
  });

  it('희소형: 엣지 1개도 정상 처리', () => {
    const ego: EgoGraphResponse = {
      center: { symbol: 'X', name: 'X' },
      nodes: [
        { symbol: 'X', name: 'X', sector: '', industry_bucket: null },
        { symbol: 'Y', name: 'Y', sector: '', industry_bucket: '금융·결제·거래소' },
      ],
      edges: [edge({ source: 'X', target: 'Y', relation_type: 'PEER_OF', has_peer_source: true, truth_score: 50 })],
      meta: { total_edges: 1, returned: 1, filtered_by: { min_score: 0, types: null, limit: 200, trend_window: 30 } },
    };
    const mm = egoToMindmap(ego);
    expect(mm.branches).toHaveLength(1);
    expect(mm.branches[0].subgroups[0].label).toBe('금융·결제·거래소');
  });

  it('industry 결측형: null bucket → 미분류 산업 하위그룹', () => {
    const ego: EgoGraphResponse = {
      center: { symbol: 'X', name: 'X' },
      nodes: [
        { symbol: 'X', name: 'X', sector: '', industry_bucket: null },
        { symbol: 'Z', name: 'Z', sector: '', industry_bucket: null },
      ],
      edges: [edge({ source: 'X', target: 'Z', relation_type: 'PEER_OF', has_industry_source: true, truth_score: 30 })],
      meta: { total_edges: 1, returned: 1, filtered_by: { min_score: 0, types: null, limit: 200, trend_window: 30 } },
    };
    const mm = egoToMindmap(ego);
    expect(mm.branches[0].subgroups[0].label).toBe('미분류 산업');
  });
});
