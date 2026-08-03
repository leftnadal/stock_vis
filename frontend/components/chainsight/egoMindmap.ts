/**
 * egoToMindmap — ego API 응답 → 마인드맵(맵-3) 3층 구조 (⑳-3 S3-MINDMAP S4)
 *
 * 순수 변환 함수(React 무의존, vitest 단독). 서빙 데이터를 접힘 카테고리 + 하위 그룹으로 조직.
 *
 * 3층 체계:
 *  L1 (SEC 도메인): relation_domain(승인본 태그) 보유 SEC 관계 → 태그별 상위 가지.
 *                   무태그 SEC 관계는 관계 유형별 "유형 수납" 가지로 폴백.
 *  L2 (시장 Peer):  PEER_OF → has_peer_source(경쟁·Peer) / 동종산업 상위 구분 +
 *                   상대 노드 industry_bucket 하위 그룹.
 *  L3 (뉴스):       CO_MENTIONED → "뉴스 동반언급" 단일 가지(기사 태그 하위그룹은 향후).
 *  PRICE_CORRELATED 는 마인드맵에서 제외(Peer 중복) — 제외 건수만 투명화.
 */

import type { EgoGraphResponse, EgoEdge } from '@/types/chainsight';

export type MindmapBranchKind =
  | 'sec_domain'   // L1 태그
  | 'sec_untagged' // L1 무태그(유형 수납)
  | 'peer'         // L2 경쟁·Peer
  | 'industry'     // L2 동종 산업
  | 'co_mention';  // L3 뉴스 동반언급

export interface MindmapLeaf {
  symbol: string;
  name: string;
  relation_type: string;
  truth_score: number;
  grade: string;
  industry_bucket: string | null;
}

export interface MindmapSubgroup {
  key: string;
  label: string; // industry_bucket (없으면 "미분류 산업")
  count: number;
  leaves: MindmapLeaf[];
}

export interface MindmapBranch {
  key: string;
  label: string;
  kind: MindmapBranchKind;
  isSec: boolean; // 시각 구분(SEC 근거 vs 시장 파생)
  count: number;
  leaves: MindmapLeaf[]; // subgroup 없는 가지의 직접 하위
  subgroups: MindmapSubgroup[]; // L2 industry 하위 그룹
}

export interface MindmapData {
  center: { symbol: string; name: string };
  branches: MindmapBranch[];
  excludedPriceCorrelated: number;
}

const SEC_TYPES = new Set(['SUPPLIES_TO', 'COMPETES_WITH', 'DEPENDS_ON', 'PARTNER_WITH']);

const SEC_TYPE_LABEL: Record<string, string> = {
  SUPPLIES_TO: '공급 관계',
  COMPETES_WITH: '경쟁 관계',
  DEPENDS_ON: '의존 관계',
  PARTNER_WITH: '협력 관계',
};

const UNCLASSIFIED_INDUSTRY = '미분류 산업';

function sortLeaves(leaves: MindmapLeaf[]): MindmapLeaf[] {
  return [...leaves].sort((a, b) => b.truth_score - a.truth_score);
}

/** ego 응답 → 마인드맵 3층 구조. */
export function egoToMindmap(ego: EgoGraphResponse): MindmapData {
  const centerSym = ego.center.symbol;
  const nodeName = new Map<string, string>(ego.nodes.map((n) => [n.symbol, n.name || n.symbol]));
  const nodeBucket = new Map<string, string | null>(
    ego.nodes.map((n) => [n.symbol, n.industry_bucket ?? null]),
  );

  // 가지 누적기: key → branch(leaves/subgroups 임시 맵)
  interface Acc {
    branch: MindmapBranch;
    subMap: Map<string, MindmapSubgroup>;
  }
  const acc = new Map<string, Acc>();
  let excludedPriceCorrelated = 0;

  function ensureBranch(key: string, label: string, kind: MindmapBranchKind, isSec: boolean): Acc {
    let a = acc.get(key);
    if (!a) {
      a = {
        branch: { key, label, kind, isSec, count: 0, leaves: [], subgroups: [] },
        subMap: new Map(),
      };
      acc.set(key, a);
    }
    return a;
  }

  function leafOf(edge: EgoEdge, neighbor: string): MindmapLeaf {
    return {
      symbol: neighbor,
      name: nodeName.get(neighbor) || neighbor,
      relation_type: edge.relation_type,
      truth_score: edge.truth_score,
      grade: edge.grade,
      industry_bucket: nodeBucket.get(neighbor) ?? null,
    };
  }

  function addToSubgroup(a: Acc, leaf: MindmapLeaf): void {
    const bucket = leaf.industry_bucket || UNCLASSIFIED_INDUSTRY;
    let sg = a.subMap.get(bucket);
    if (!sg) {
      sg = { key: bucket, label: bucket, count: 0, leaves: [] };
      a.subMap.set(bucket, sg);
    }
    sg.leaves.push(leaf);
    sg.count += 1;
    a.branch.count += 1;
  }

  for (const edge of ego.edges) {
    const neighbor = edge.source === centerSym ? edge.target : edge.source;
    const rtype = edge.relation_type;

    if (rtype === 'PRICE_CORRELATED') {
      excludedPriceCorrelated += 1;
      continue;
    }

    const leaf = leafOf(edge, neighbor);

    if (edge.relation_domain) {
      // L1: SEC 도메인 태그
      const a = ensureBranch(`dom:${edge.relation_domain}`, edge.relation_domain, 'sec_domain', true);
      a.branch.leaves.push(leaf);
      a.branch.count += 1;
    } else if (SEC_TYPES.has(rtype)) {
      // L1 폴백: 무태그 SEC → 유형 수납
      const label = SEC_TYPE_LABEL[rtype] || rtype;
      const a = ensureBranch(`sectype:${rtype}`, label, 'sec_untagged', true);
      a.branch.leaves.push(leaf);
      a.branch.count += 1;
    } else if (rtype === 'PEER_OF' || rtype === 'PEER') {
      // L2: 경쟁·Peer vs 동종산업 상위 구분 + industry 하위 그룹
      const isPeer = !!edge.has_peer_source;
      const a = isPeer
        ? ensureBranch('peer', '경쟁·Peer 기업', 'peer', false)
        : ensureBranch('industry', '동종 산업', 'industry', false);
      addToSubgroup(a, leaf);
    } else if (rtype === 'CO_MENTIONED') {
      // L3: 뉴스 동반언급(단일)
      const a = ensureBranch('co_mention', '뉴스 동반언급', 'co_mention', false);
      a.branch.leaves.push(leaf);
      a.branch.count += 1;
    } else {
      // 기타 시장 관계 → 유형 수납(무태그 폴백과 동일 처리)
      const a = ensureBranch(`sectype:${rtype}`, rtype, 'sec_untagged', false);
      a.branch.leaves.push(leaf);
      a.branch.count += 1;
    }
  }

  // 마무리: subgroups 정렬·leaves 정렬, 가지 순서(SEC 먼저·건수 desc)
  const branches: MindmapBranch[] = [];
  for (const { branch, subMap } of acc.values()) {
    branch.leaves = sortLeaves(branch.leaves);
    branch.subgroups = [...subMap.values()]
      .map((sg) => ({ ...sg, leaves: sortLeaves(sg.leaves) }))
      .sort((a, b) => b.count - a.count);
    branches.push(branch);
  }
  branches.sort((a, b) => {
    if (a.isSec !== b.isSec) return a.isSec ? -1 : 1; // SEC 먼저
    return b.count - a.count;
  });

  return {
    center: { symbol: centerSym, name: ego.center.name || centerSym },
    branches,
    excludedPriceCorrelated,
  };
}
