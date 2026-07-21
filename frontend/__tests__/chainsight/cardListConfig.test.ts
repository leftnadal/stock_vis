/**
 * cardListConfig 순수 함수 (⑳-2 S2) — 정렬·배지 매핑·노드맵.
 */
import { describe, it, expect } from 'vitest';
import { sortEdges, relationBadge, buildNodeMap } from '@/components/chainsight/cardListConfig';
import type { EgoEdge, EgoNode } from '@/types/chainsight';

function edge(target: string, score: number, last: string | null): EgoEdge {
  return {
    source: 'X',
    target,
    relation_type: 'PEER_OF',
    truth_score: score,
    evidence_count: 0,
    last_mentioned: last,
    trend: { direction: 'flat', delta: 0, points: [] },
  };
}

describe('sortEdges', () => {
  it('confidence: truth_score 내림차순 (기본)', () => {
    const r = sortEdges([edge('A', 40, null), edge('B', 90, null), edge('C', 60, null)], 'confidence');
    expect(r.map((e) => e.target)).toEqual(['B', 'C', 'A']);
  });

  it('recent: last_mentioned 내림차순, null은 뒤로', () => {
    const r = sortEdges(
      [edge('A', 10, '2026-07-10'), edge('B', 10, null), edge('C', 10, '2026-07-20')],
      'recent',
    );
    expect(r.map((e) => e.target)).toEqual(['C', 'A', 'B']);
  });

  it('원본 배열을 변형하지 않는다', () => {
    const src = [edge('A', 40, null), edge('B', 90, null)];
    sortEdges(src, 'confidence');
    expect(src.map((e) => e.target)).toEqual(['A', 'B']);
  });
});

describe('relationBadge', () => {
  it('기존 범례 용어를 재사용한다 (신규색 0)', () => {
    expect(relationBadge('PEER_OF').label).toBe('Peer');
    expect(relationBadge('COMPETES_WITH').label).toBe('경쟁');
    expect(relationBadge('SUPPLIES_TO').label).toBe('공급');
    expect(relationBadge('CO_MENTIONED').label).toBe('동시출현');
  });
  it('미지 유형은 관련 폴백', () => {
    expect(relationBadge('UNKNOWN_XYZ').label).toBe('관련');
  });
  it('color 는 hex 문자열', () => {
    expect(relationBadge('PEER_OF').color).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });
});

describe('buildNodeMap', () => {
  it('심볼 → 노드 맵', () => {
    const nodes: EgoNode[] = [
      { symbol: 'A', name: 'Alpha', sector: 'Tech' },
      { symbol: 'B', name: 'Beta', sector: 'Fin' },
    ];
    const m = buildNodeMap(nodes);
    expect(m['A'].name).toBe('Alpha');
    expect(m['B'].sector).toBe('Fin');
  });
});
