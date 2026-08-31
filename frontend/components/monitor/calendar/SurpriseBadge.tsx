// 서프라이즈 뱃지(b-beat/b-miss, P1-i). surprise=null(미발표·계산 실패) → 비표시.
import { badgeClass, SURPRISE_BADGE_CLASS } from './eventColors';
import type { EventKind, EventSurprise } from '@/types/eventCalendar';

interface SurpriseBadgeProps {
  surprise: EventSurprise | null;
  kind: EventKind;
}

export function SurpriseBadge({ surprise, kind }: SurpriseBadgeProps) {
  if (!surprise) return null;

  const sign = surprise.pct >= 0 ? '+' : '';
  const pctText = `${sign}${surprise.pct.toFixed(1)}%`;
  const label = kind === 'earnings' ? `EPS ${pctText} ${surprise.direction}` : `서프라이즈 ${pctText}`;

  return (
    <span
      data-testid={`surprise-badge-${surprise.direction}`}
      className={badgeClass(SURPRISE_BADGE_CLASS[surprise.direction])}
    >
      {label}
    </span>
  );
}
