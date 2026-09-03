// 관계 뱃지 (EVT-CHAIN-1). relation_type → 중립 한글 라벨 + truth 점수.
// 부호 중립(§6): 모든 관계 유형이 단일 색(teal) — 방향/센티먼트 색 금지. truth는 중립 회색.
// 라벨 매핑 = §0-4⑴ 실측 RELATION_TYPE_CHOICES 기준. 미지 유형 = 원문 코드(날조 금지).
import { badgeClass } from '@/components/monitor/calendar/eventColors';

// RelationConfidence.RELATION_TYPE_CHOICES 실측(방향 함의 제거한 중립 라벨).
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
}

export function RelationBadge({ relationType, truthScore }: RelationBadgeProps) {
  const label = RELATION_LABEL[relationType] ?? relationType; // 미지 = 원문(날조 금지)
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
