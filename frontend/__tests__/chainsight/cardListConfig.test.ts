/**
 * cardListConfig 순수 함수 (⑳-2 S2 → ⑳-G) — 정렬·배지·노드맵·등급·섹션.
 */
import { describe, it, expect } from 'vitest';
import {
  sortEdges,
  relationBadge,
  buildNodeMap,
  gradeBadge,
  groupEdgesBySection,
  sortInSection,
  SECTION_ORDER,
} from '@/components/chainsight/cardListConfig';
import type { EgoEdge, EgoNode } from '@/types/chainsight';

function edge(partial: Partial<EgoEdge> & { target: string }): EgoEdge {
  return {
    source: 'X',
    relation_type: 'PEER_OF',
    truth_score: 85,
    evidence_count: 0,
    last_mentioned: null,
    trend: { direction: 'flat', delta: 0, points: [] },
    grade: 'confirmed',
    grade_source: 'market_peer',
    basis_summary: '',
    last_observed_at: null,
    ...partial,
  };
}

describe('sortEdges (레거시 하위호환)', () => {
  it('confidence: truth_score 내림차순 (기본)', () => {
    const r = sortEdges(
      [edge({ target: 'A', truth_score: 40 }), edge({ target: 'B', truth_score: 90 }), edge({ target: 'C', truth_score: 60 })],
      'confidence',
    );
    expect(r.map((e) => e.target)).toEqual(['B', 'C', 'A']);
  });

  it('원본 배열을 변형하지 않는다', () => {
    const src = [edge({ target: 'A', truth_score: 40 }), edge({ target: 'B', truth_score: 90 })];
    sortEdges(src, 'confidence');
    expect(src.map((e) => e.target)).toEqual(['A', 'B']);
  });
});

describe('relationBadge', () => {
  it('기존 범례 용어를 재사용한다 (신규색 0)', () => {
    expect(relationBadge('PEER_OF').label).toBe('Peer');
    expect(relationBadge('COMPETES_WITH').label).toBe('경쟁');
    expect(relationBadge('SUPPLIES_TO').label).toBe('공급');
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

describe('gradeBadge (⑳-G)', () => {
  it('등급+소스 병기: "확정 · 공시"', () => {
    expect(gradeBadge('confirmed', 'sec_filing').label).toBe('확정 · 공시');
    expect(gradeBadge('likely', 'market_peer').label).toBe('유력 · 동종');
    expect(gradeBadge('observed', 'co_mention').label).toBe('관찰 · 뉴스');
  });
  it('소스 unknown이면 등급만', () => {
    expect(gradeBadge('confirmed', 'unknown').label).toBe('확정');
  });
  it('색은 등급별 hex', () => {
    expect(gradeBadge('confirmed', 'sec_filing').color).toMatch(/^#[0-9A-Fa-f]{6}$/);
    expect(gradeBadge('confirmed', 'sec_filing').color).not.toBe(gradeBadge('observed', 'sec_filing').color);
  });
});

describe('sortInSection (⑳-G tie-break)', () => {
  it('등급 내림차순 → 근거수 → 심볼 알파벳', () => {
    const r = sortInSection([
      edge({ target: 'B', grade: 'observed', evidence_count: 5 }),
      edge({ target: 'A', grade: 'confirmed', evidence_count: 1 }),
      edge({ target: 'C', grade: 'confirmed', evidence_count: 1 }),
      edge({ target: 'D', grade: 'confirmed', evidence_count: 9 }),
    ]);
    // confirmed 먼저(D ev9 → A/C ev1 알파벳 A<C), observed 마지막(B)
    expect(r.map((e) => e.target)).toEqual(['D', 'A', 'C', 'B']);
  });
});

describe('groupEdgesBySection (⑳-G)', () => {
  it('유형→섹션 배분 + 순서(공급→경쟁→Peer→시장)', () => {
    const g = groupEdgesBySection([
      edge({ target: 'P', relation_type: 'PEER_OF' }),
      edge({ target: 'S', relation_type: 'SUPPLIES_TO' }),
      edge({ target: 'C', relation_type: 'COMPETES_WITH' }),
      edge({ target: 'M', relation_type: 'CO_MENTIONED' }),
    ]);
    expect(g.map((s) => s.key)).toEqual(['supply', 'compete', 'peer', 'market']);
    expect(g[0].edges[0].target).toBe('S');
  });

  it('빈 섹션은 제외', () => {
    const g = groupEdgesBySection([edge({ target: 'P', relation_type: 'PEER_OF' })]);
    expect(g.map((s) => s.key)).toEqual(['peer']);
  });

  it('미지 유형은 기타 섹션 폴백', () => {
    const g = groupEdgesBySection([edge({ target: 'X', relation_type: 'MYSTERY' })]);
    expect(g.map((s) => s.key)).toEqual(['other']);
  });

  it('SECTION_ORDER 기본 순서 상수 고정', () => {
    expect(SECTION_ORDER.map((s) => s.key)).toEqual(['supply', 'compete', 'peer', 'market', 'other']);
  });
});
