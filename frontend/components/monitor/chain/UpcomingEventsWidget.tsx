// 미니 이벤트 위젯 (EVT-CHAIN-1 / D-EVT-FE1). 시드 자신의 다음 어닝·배당락 pill.
// 연합 읽기 재사용(seed_events = build_chain_feed) — 신규 쿼리 없음. "캘린더에서 보기 →"로 Phase1 동선.
import Link from 'next/link';

import { badgeClass, KIND_BADGE_CLASS, KIND_LABEL } from '@/components/monitor/calendar/eventColors';
import { TrustBadge } from '@/components/monitor/calendar/TrustBadge';
import { fmtDateShort, fmtDday, formatDetail } from '@/lib/monitor/calendarFormat';
import type { EventItem } from '@/types/eventCalendar';

const PILL = 'inline-flex items-center gap-1.5 rounded-md border border-gray-200 px-2.5 py-1 text-xs dark:border-gray-700';

function EarningsPill({ ev }: { ev: EventItem }) {
  return (
    <span data-testid="widget-earnings-pill" className={PILL}>
      <span className={badgeClass(KIND_BADGE_CLASS.earnings)}>{KIND_LABEL.earnings}</span>
      <span className="font-mono font-bold text-blue-600 dark:text-blue-400">{fmtDday(ev.d_day)}</span>
      <span className="text-gray-500 dark:text-gray-400">{fmtDateShort(ev.event_date_et)}</span>
      <span className="text-gray-600 dark:text-gray-300">{formatDetail(ev)}</span>
      <TrustBadge trust={ev.date_trust} observedCount={ev.date_observed_count} />
    </span>
  );
}

interface Props {
  seedEvents: EventItem[];
}

export function UpcomingEventsWidget({ seedEvents }: Props) {
  const nextEarn = seedEvents.find((e) => e.kind === 'earnings');
  const nextDiv = seedEvents.find((e) => e.kind === 'dividend');
  const hasAny = Boolean(nextEarn || nextDiv);

  return (
    <div
      data-testid="upcoming-widget"
      className="my-3 rounded-lg border border-gray-200 bg-white px-3 py-2.5 dark:border-gray-800 dark:bg-gray-900"
    >
      <div className="mb-1.5 flex items-baseline gap-2 text-xs text-gray-400">
        <b className="text-sm text-gray-800 dark:text-gray-200">다가오는 이벤트</b>
        <span>· 시드 자신 · 원장 연합 읽기</span>
        <Link href="/monitor/calendar" className="ml-auto text-blue-600 hover:underline dark:text-blue-400">
          캘린더에서 보기 →
        </Link>
      </div>

      {!hasAny ? (
        <span data-testid="widget-empty" className="text-xs text-gray-400">
          예정 이벤트 없음
        </span>
      ) : (
        <div className="flex flex-wrap gap-2">
          {nextEarn && <EarningsPill ev={nextEarn} />}
          {nextDiv ? (
            <span data-testid="widget-dividend-pill" className={PILL}>
              <span className={badgeClass(KIND_BADGE_CLASS.dividend)}>{KIND_LABEL.dividend}</span>
              <span className="font-mono font-bold text-blue-600 dark:text-blue-400">
                {fmtDday(nextDiv.d_day)}
              </span>
              <span className="text-gray-500 dark:text-gray-400">{fmtDateShort(nextDiv.event_date_et)}</span>
            </span>
          ) : (
            <span data-testid="widget-no-dividend" className={PILL}>
              <span className={badgeClass(KIND_BADGE_CLASS.dividend)}>{KIND_LABEL.dividend}</span>
              <span className="text-gray-400">없음</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}
