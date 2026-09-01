// 서프라이즈 뱃지(b-beat/b-miss, P1-i). surprise=null(미발표·계산 실패) → 비표시.
// EVT-4B STEP2(FE-TUNE-1 T2 §2-6): |pct| > 200%는 분모(예상치)가 0에 가까워 퍼센트 자체가
// 오도하므로 뱃지는 "beat"/"miss"만 남긴다 — 실제 수치는 EventRow 상세 열(formatDetail의
// "EPS 실제 vs 예상 예상")이 이미 주표기로 보여준다.
import { badgeClass, SURPRISE_BADGE_CLASS } from './eventColors';
import type { EventKind, EventSurprise } from '@/types/eventCalendar';

const EXTREME_PCT_THRESHOLD = 200;

interface SurpriseBadgeProps {
  surprise: EventSurprise | null;
  kind: EventKind;
}

export function SurpriseBadge({ surprise, kind }: SurpriseBadgeProps) {
  if (!surprise) return null;

  const sign = surprise.pct >= 0 ? '+' : '';
  const pctText = `${sign}${surprise.pct.toFixed(1)}%`;
  const isExtreme = Math.abs(surprise.pct) > EXTREME_PCT_THRESHOLD;
  const label =
    kind === 'earnings'
      ? isExtreme
        ? surprise.direction
        : `EPS ${pctText} ${surprise.direction}`
      : `서프라이즈 ${pctText}`;

  return (
    <span
      data-testid={`surprise-badge-${surprise.direction}`}
      className={badgeClass(SURPRISE_BADGE_CLASS[surprise.direction])}
    >
      {label}
    </span>
  );
}
