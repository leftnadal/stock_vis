// 날짜 신뢰 뱃지(b-stable/b-fluid/b-unk, P1-ii). CalendarEvent kind만 값을 가진다 —
// macro/holiday/split_effective은 date_trust=null이라 컴포넌트가 아무것도 그리지 않는다.
import { badgeClass, TRUST_BADGE_CLASS } from './eventColors';
import type { DateTrust } from '@/types/eventCalendar';

interface TrustBadgeProps {
  trust: DateTrust | null;
  observedCount: number | null;
}

export function TrustBadge({ trust, observedCount }: TrustBadgeProps) {
  if (!trust) return null;

  let label: string;
  if (trust === 'unconfirmed') {
    label = '미확정 · stale';
  } else if (trust === 'stable') {
    label = `안정 · 관측 ${observedCount ?? 0}회`;
  } else {
    label = observedCount ? `유동 · 관측 ${observedCount}회` : '유동 · 신규';
  }

  return (
    <span data-testid={`trust-badge-${trust}`} className={badgeClass(TRUST_BADGE_CLASS[trust])}>
      {label}
    </span>
  );
}
