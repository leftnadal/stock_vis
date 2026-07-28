import { describe, it, expect } from 'vitest';
import {
  qualificationChips,
  showsBasis,
  gradeLine,
} from '@/components/chainsight/cardListConfig';
import type { EgoEdge } from '@/types/chainsight';

// ⑳-3 S2 C: 정성화 헬퍼(칩 분화·근거 게이트·등급 라벨)
function edge(over: Partial<EgoEdge>): EgoEdge {
  return {
    source: 'AAA', target: 'BBB', relation_type: 'PEER_OF', truth_score: 60,
    evidence_count: 0, last_mentioned: null,
    trend: { direction: 'flat', delta: 0, points: [] },
    grade: 'likely', grade_source: 'market_peer', basis_summary: '',
    last_observed_at: null,
    ...over,
  } as EgoEdge;
}

describe('qualificationChips (C-1)', () => {
  it('PEER: peer+industry → [Peer·FMP, 동종산업]', () => {
    expect(qualificationChips(edge({ has_peer_source: true, has_industry_source: true })))
      .toEqual(['Peer·FMP', '동종산업']);
  });
  it('PEER: industry만 → [동종산업]', () => {
    expect(qualificationChips(edge({ has_peer_source: false, has_industry_source: true })))
      .toEqual(['동종산업']);
  });
  it('PEER: 출처 없음 → [Peer] 폴백', () => {
    expect(qualificationChips(edge({}))).toEqual(['Peer']);
  });
  it('CO_MENTIONED: N회 병기', () => {
    expect(qualificationChips(edge({ relation_type: 'CO_MENTIONED', co_mention_count: 7 })))
      .toEqual(['뉴스 동시출현 7회']);
  });
  it('SEC 유형: 유형 라벨 1칩', () => {
    expect(qualificationChips(edge({ relation_type: 'SUPPLIES_TO' }))).toEqual(['공급']);
  });
});

describe('showsBasis (C-2)', () => {
  it('SEC 4종 + CO_MENTIONED이고 basis 있으면 노출', () => {
    expect(showsBasis(edge({ relation_type: 'COMPETES_WITH', basis_summary: 'SEC 10-K: ...' }))).toBe(true);
    expect(showsBasis(edge({ relation_type: 'CO_MENTIONED', basis_summary: '뉴스 동시출현 3회' }))).toBe(true);
  });
  it('PEER는 basis 있어도 문장 미노출(등급만)', () => {
    expect(showsBasis(edge({ relation_type: 'PEER_OF', basis_summary: 'Peer 관계 + 같은 산업' }))).toBe(false);
  });
  it('basis 비면 미노출', () => {
    expect(showsBasis(edge({ relation_type: 'SUPPLIES_TO', basis_summary: '' }))).toBe(false);
  });
});

describe('gradeLine (C-3)', () => {
  it('confirmed → 확인됨 + truth_score', () => {
    expect(gradeLine(edge({ status: 'confirmed', truth_score: 85 }))).toBe('확인됨 85');
  });
  it('probable → 추정', () => {
    expect(gradeLine(edge({ status: 'probable', truth_score: 60 }))).toBe('추정 60');
  });
  it('status 없거나 truth_score 0이면 점수 생략/빈값', () => {
    expect(gradeLine(edge({ status: 'confirmed', truth_score: 0 }))).toBe('확인됨');
    expect(gradeLine(edge({ status: undefined, truth_score: 60 }))).toBe('');
  });
});
