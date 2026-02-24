'use client';

import { RelationshipTag } from '@/types/chainSight';
import { getTagClasses, getTagLabel } from '@/utils/relationshipTagStyles';

interface RelationshipTagBadgeProps {
  tag: RelationshipTag;
}

/**
 * 관계 태그 pill 컴포넌트 (Phase 6)
 *
 * 이모지 없는 컬러 pill 태그로 관계 정보를 표시합니다.
 * 예: [반도체] [뉴스 5건] [TSMC 공급 매출25%]
 */
export default function RelationshipTagBadge({ tag }: RelationshipTagBadgeProps) {
  const classes = getTagClasses(tag.type);
  const label = getTagLabel(tag.type, tag.label);

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${classes}`}
    >
      <span>{label}</span>
      {tag.detail && (
        <span className="opacity-75">{tag.detail}</span>
      )}
    </span>
  );
}
