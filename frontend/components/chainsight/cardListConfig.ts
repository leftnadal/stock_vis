/**
 * 관계 카드 리스트 설정 상수 (⑳-2 S2 → ⑳-G 정직화) — 정렬·표시·등급 단일 소스.
 * (⑳-1 leaderboardConfig 패턴: 매직넘버·매핑을 컴포넌트 밖으로 분리.)
 *
 * ⑳-G: 연속 신뢰도 바 폐지 → 계단 등급 라벨. 유형별 섹션 분리 + 섹션 내 tie-break.
 * 등급/소스 문구·섹션 순서·정렬 키를 여기서 단일 관리(⑳-G DoD 상수 분리).
 */

import { getRelationStyle } from './graphStyles';
import type { EgoEdge, EgoNode, EgoGrade, EgoGradeSource } from '@/types/chainsight';

/** 기본 표시 개수(더 보기 전) + 더 보기 증가량 */
export const CARD_LIST = {
  initialVisible: 12,
  loadMoreStep: 12,
} as const;

export type CardSortKey = 'confidence' | 'recent';
export const DEFAULT_SORT: CardSortKey = 'confidence';

// ── ⑳-G 등급 라벨·색 (계단값→등급 코드는 서버가 부여, FE는 문구/색만) ──

/** 등급 코드 → 한글 문구. 연속 신뢰도가 아니라 계단 등급임을 표현. */
export const GRADE_LABELS: Record<EgoGrade, string> = {
  confirmed: '확정',
  likely: '유력',
  observed: '관찰',
  unverified: '미확인',
};

/** 등급 코드 → 배지 색(텍스트/보더). 신규 최소 팔레트(등급 4단 구분). */
export const GRADE_COLORS: Record<EgoGrade, string> = {
  confirmed: '#16A34A', // green-600
  likely: '#2563EB', // blue-600
  observed: '#6B7280', // gray-500
  unverified: '#9CA3AF', // gray-400
};

/** 등급 정렬 순위(내림차순 tie-break용). */
export const GRADE_RANK: Record<EgoGrade, number> = {
  confirmed: 3,
  likely: 2,
  observed: 1,
  unverified: 0,
};

/** 근거 소스 코드 → 짧은 병기 라벨. SEC 공시 계열은 basis_summary가 근거. */
export const GRADE_SOURCE_LABELS: Record<EgoGradeSource, string> = {
  sec_filing: '공시',
  market_peer: '동종',
  co_mention: '뉴스',
  price_corr: '주가',
  unknown: '',
};

/** 등급 배지 텍스트/색: "확정 · 공시"처럼 등급+소스 병기(소스 없으면 등급만). */
export function gradeBadge(
  grade: EgoGrade,
  source: EgoGradeSource,
): { label: string; color: string } {
  const g = GRADE_LABELS[grade] ?? grade;
  const s = GRADE_SOURCE_LABELS[source] ?? '';
  return { label: s ? `${g} · ${s}` : g, color: GRADE_COLORS[grade] ?? GRADE_COLORS.unverified };
}

// ── ⑳-G 유형별 섹션 (순서 상수: 공급→경쟁→Peer→시장→기타) ──

export interface CardSection {
  key: string;
  label: string;
  /** 이 섹션에 속하는 relation_type 목록(빈 배열 = 기타 폴백). */
  types: string[];
  /** 섹션 헤더 한 줄 설명(근거 소스 요약). */
  desc: string;
}

export const SECTION_ORDER: CardSection[] = [
  {
    key: 'supply',
    label: '공급망',
    types: ['SUPPLIES_TO', 'DEPENDS_ON', 'PARTNER_WITH'],
    desc: '공시(10-K) 기반 공급·의존·협력',
  },
  {
    key: 'compete',
    label: '경쟁',
    types: ['COMPETES_WITH'],
    desc: '공시(10-K) 기반 경쟁 관계',
  },
  {
    key: 'peer',
    label: 'Peer',
    types: ['PEER_OF', 'PEER'],
    desc: '동종 업계·산업 분류 기반',
  },
  {
    key: 'market',
    label: '시장 신호',
    types: ['CO_MENTIONED', 'PRICE_CORRELATED'],
    desc: '뉴스 동시출현·주가 상관(참고)',
  },
  {
    key: 'other',
    label: '기타',
    types: [], // 폴백: 위 어디에도 안 속한 유형
    desc: '기타 관계',
  },
];

/**
 * 관계 유형 → 배지(색·라벨). 그래프 RELATION_STYLES 재사용(신규색 0).
 * 섹션 헤더/기타 표기에 보조 사용.
 */
export function relationBadge(relationType: string): { color: string; label: string } {
  const s = getRelationStyle(relationType);
  return { color: s.color, label: s.label };
}

/** 이웃 노드 심볼 → 노드 메타 맵(카드가 회사명·섹터 조회용). */
export function buildNodeMap(nodes: EgoNode[]): Record<string, EgoNode> {
  const m: Record<string, EgoNode> = {};
  for (const n of nodes) m[n.symbol] = n;
  return m;
}

/**
 * 섹션 내 tie-break 정렬(⑳-G): 등급 내림차순 → 뉴스 근거수 내림차순 → 심볼 알파벳.
 * ⑳-F Q3: 서버는 truth_score 단일 키(동점 순서 미정의)라 FE가 안정 정렬을 확정한다.
 */
export function sortInSection(edges: EgoEdge[]): EgoEdge[] {
  return [...edges].sort(
    (a, b) =>
      (GRADE_RANK[b.grade] ?? 0) - (GRADE_RANK[a.grade] ?? 0) ||
      (b.evidence_count ?? 0) - (a.evidence_count ?? 0) ||
      a.target.localeCompare(b.target),
  );
}

/** 섹션 정의 목록(폴백 포함) — key로 조회. */
function sectionForType(relationType: string): CardSection {
  const found = SECTION_ORDER.find((s) => s.types.includes(relationType));
  if (found) return found;
  return SECTION_ORDER.find((s) => s.key === 'other')!;
}

export interface GroupedSection extends CardSection {
  edges: EgoEdge[];
}

/**
 * 엣지를 유형별 섹션으로 그룹핑 + 섹션 내 정렬. 빈 섹션은 제외.
 * 순서는 SECTION_ORDER 고정(공급→경쟁→Peer→시장→기타).
 */
export function groupEdgesBySection(edges: EgoEdge[]): GroupedSection[] {
  const byKey: Record<string, EgoEdge[]> = {};
  for (const s of SECTION_ORDER) byKey[s.key] = [];
  for (const e of edges) byKey[sectionForType(e.relation_type).key].push(e);
  return SECTION_ORDER.map((s) => ({ ...s, edges: sortInSection(byKey[s.key]) })).filter(
    (s) => s.edges.length > 0,
  );
}

/**
 * (레거시 ⑳-2) 전역 카드 정렬: confidence / recent.
 * ⑳-G 섹션 뷰에서는 groupEdgesBySection이 대체하나, 하위호환 위해 유지.
 */
export function sortEdges(edges: EgoEdge[], sortKey: CardSortKey): EgoEdge[] {
  const copy = [...edges];
  if (sortKey === 'recent') {
    copy.sort((a, b) => (b.last_mentioned ?? '').localeCompare(a.last_mentioned ?? ''));
  } else {
    copy.sort((a, b) => b.truth_score - a.truth_score);
  }
  return copy;
}
