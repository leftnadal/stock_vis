// 관계 뱃지 (EVT-CHAIN-1 / CHAIN-1a). 시드 기준 역할(방향성 유형) 우선, 아니면 관계 유형 라벨.
// 부호 중립(앵커 §6): 금지 대상은 호재/악재 판단 — 관계 역할 라벨(공급사/고객/피어)은 허용.
// 단일 색(teal) — 유형·역할별 색 분기 없음(방향 색 금지). truth는 중립 회색.
// 라벨 매핑 = §0-4⑴ 실측 RELATION_TYPE_CHOICES 기준. 미지 유형 = 원문 코드(날조 금지).
import { badgeClass } from '@/components/monitor/calendar/eventColors';
import type { ChainRole } from '@/types/chainFeed';

// 시드 기준 역할 라벨(SEC 방향 규약 도출·CHAIN-1a). ACQUIRED는 규약 불명확 → 역할 없음(중립).
const ROLE_LABEL: Record<ChainRole, string> = {
  supplier: '공급사', // 이웃 → 시드 공급
  customer: '고객', // 시드 → 이웃 공급
  dependency: '의존 대상', // 시드 → 이웃 의존
  dependent: '의존 기업', // 이웃 → 시드 의존
};

// RelationConfidence.RELATION_TYPE_CHOICES 실측(대칭 유형·역할 없을 때 폴백).
const RELATION_LABEL: Record<string, string> = {
  PEER_OF: '피어',
  SUPPLIES_TO: '공급망',
  COMPETES_WITH: '경쟁',
  CO_MENTIONED: '동시언급',
  PRICE_CORRELATED: '가격동조',
  HAS_THEME: '테마',
  HELD_BY_SAME_FUND: '동일펀드',
  PARTNER_WITH: '파트너',
  DEPENDS_ON: '연관',
  ACQUIRED: '인수',
};

// 단일 중립 색(부호 중립) — 관계 유형별 색 분기 없음.
const REL_CLASS = 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300';
const TRUTH_CLASS =
  'bg-slate-100 text-slate-600 font-mono dark:bg-slate-800 dark:text-slate-300';

interface RelationBadgeProps {
  relationType: string;
  truthScore: number; // 도메인 [0,1] → 표시 ×100
  role?: ChainRole | null; // 방향성 유형 역할(있으면 우선)
}

export function RelationBadge({ relationType, truthScore, role }: RelationBadgeProps) {
  // 역할(방향성 도출) 우선 → 없으면 관계 유형 라벨 → 미지는 원문(날조 금지).
  const label = (role && ROLE_LABEL[role]) || RELATION_LABEL[relationType] || relationType;
  const shown = Math.round(truthScore * 100);
  return (
    <>
      <span data-testid={`relation-badge-${relationType}`} className={badgeClass(REL_CLASS)}>
        {label}
      </span>
      <span data-testid="truth-badge" className={badgeClass(TRUTH_CLASS)}>
        truth {shown}
      </span>
    </>
  );
}
