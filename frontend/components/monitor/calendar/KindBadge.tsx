// 이벤트 유형 뱃지(b-earn/b-div/b-split/b-macro/b-hol). 목업 KindBadge.
import { badgeClass, KIND_BADGE_CLASS, KIND_LABEL } from './eventColors';
import type { EventKind } from '@/types/eventCalendar';

export function KindBadge({ kind }: { kind: EventKind }) {
  return (
    <span data-testid={`kind-badge-${kind}`} className={badgeClass(KIND_BADGE_CLASS[kind])}>
      {KIND_LABEL[kind]}
    </span>
  );
}
