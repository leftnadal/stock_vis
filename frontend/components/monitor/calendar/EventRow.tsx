// 이벤트 행 — 심볼·유형뱃지·(session 값 있을 때만) 세션뱃지·상세·신뢰뱃지·시간·출처마크.
// 목업 .row 그리드(150px 1fr 200px 130px) 그대로. 휴장 행은 빗금 배경(hol-row),
// stale 행은 반투명(opacity .55, 기본은 상위 페이지가 숨김 처리 — 여기선 스타일만).
import {
  badgeClass,
  HOLIDAY_STRIPE_BG,
  IMPORTANCE_BADGE_CLASS,
  SESSION_BADGE_CLASS,
} from './eventColors';
import { KindBadge } from './KindBadge';
import { SurpriseBadge } from './SurpriseBadge';
import { TrustBadge } from './TrustBadge';
import { formatDetail, formatTime, sourceLabel } from '@/lib/monitor/calendarFormat';
import type { EventItem } from '@/types/eventCalendar';

function ImportanceBadges({ badges }: { badges: string[] }) {
  const visible = badges.filter((token) => token !== 'today');
  if (visible.length === 0) return null;
  return (
    <>
      {visible.map((token) => (
        <span
          key={token}
          data-testid={`importance-badge-${token}`}
          className={badgeClass(IMPORTANCE_BADGE_CLASS[token] ?? IMPORTANCE_BADGE_CLASS.default)}
        >
          {token.toUpperCase()}
        </span>
      ))}
    </>
  );
}

export function EventRow({ item }: { item: EventItem }) {
  const isHoliday = item.kind === 'holiday';
  const time = formatTime(item);
  const source = sourceLabel(item.sources);

  return (
    <div
      data-testid={`event-row-${item.kind}-${item.symbol ?? 'na'}`}
      style={isHoliday ? { backgroundImage: HOLIDAY_STRIPE_BG } : undefined}
      className={`grid grid-cols-[150px_1fr_200px_130px] items-center gap-2.5 border-b border-dashed border-gray-100 py-2 last:border-0 dark:border-gray-800 ${
        isHoliday ? 'rounded-md' : ''
      } ${item.status === 'stale' ? 'opacity-55' : ''}`}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        {item.symbol && <span className="font-bold text-gray-900 dark:text-gray-100">{item.symbol}</span>}
        <KindBadge kind={item.kind} />
        {item.session && (
          <span data-testid="session-badge" className={badgeClass(SESSION_BADGE_CLASS)}>
            {item.session}
          </span>
        )}
        {!item.symbol && (
          <span className="text-sm text-gray-700 dark:text-gray-200">{item.title}</span>
        )}
        {source && (
          <span
            data-testid="source-mark"
            className="rounded border border-gray-200 px-1 text-[10px] text-gray-400 dark:border-gray-700"
          >
            {source}
          </span>
        )}
      </div>

      <div className="text-xs text-gray-500 dark:text-gray-400">{formatDetail(item)}</div>

      <div className="flex flex-wrap items-center gap-1">
        <SurpriseBadge surprise={item.surprise} kind={item.kind} />
        <ImportanceBadges badges={item.badges} />
        <TrustBadge trust={item.date_trust} observedCount={item.date_observed_count} />
      </div>

      <div className="text-xs text-gray-500 dark:text-gray-400">
        <div>{time.main}</div>
        {time.sub && <div className="text-gray-400 dark:text-gray-500">{time.sub}</div>}
      </div>
    </div>
  );
}
