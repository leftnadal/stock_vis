'use client';

// 홈 이벤트 스트립(Screen S) — 다가오는 이벤트(45일, 거시 HIGH+·휴장·관심 어닝 티저 최대 2).
// 실패 격리 동형(NewsStrip/MacroStrip과 동일): API 실패·빈 응답 → 컴포넌트 자체가 null.
import Link from 'next/link';

import { IMPORTANCE_BADGE_CLASS, badgeClass } from '@/components/monitor/calendar/eventColors';
import { formatTime, fmtDday } from '@/lib/monitor/calendarFormat';
import { useEventStrip } from '@/hooks/useEventCalendar';
import type { EventItem } from '@/types/eventCalendar';

// 날짜 오름차순 정렬 후, earnings(관심 어닝 티저)는 최대 2장만 남긴다(설계 §5 "있어도 되고
// 없어도 되는" 요소 — 4호에서 on, 상한 2 확정). 그 외 kind(macro/holiday)는 상한 없음.
function sortAndCapTeasers(items: EventItem[]): EventItem[] {
  const sorted = [...items].sort((a, b) => {
    if (a.event_date_et !== b.event_date_et) return a.event_date_et < b.event_date_et ? -1 : 1;
    return (a.event_time_et ?? '') < (b.event_time_et ?? '') ? -1 : 1;
  });
  let earnCount = 0;
  return sorted.filter((item) => {
    if (item.kind !== 'earnings') return true;
    earnCount += 1;
    return earnCount <= 2;
  });
}

function cardMeta(item: EventItem): string {
  const time = formatTime(item);
  if (item.kind === 'holiday') return '';
  if (item.kind === 'earnings') {
    const eps = (item.detail as { eps_estimated?: number | null } | undefined)?.eps_estimated;
    return `관심종목 · EPS 예상 ${eps ?? '—'}`;
  }
  if (item.kind === 'macro') {
    const forecast = (item.detail as { forecast_value?: string | null } | undefined)
      ?.forecast_value;
    const parts = [forecast ? `예상 ${forecast}` : null, time.sub].filter(Boolean);
    return parts.join(' · ');
  }
  return time.sub ?? '';
}

function EventCard({ item }: { item: EventItem }) {
  const isHoliday = item.kind === 'holiday';
  const isWatchEarnings = item.kind === 'earnings';
  const isCritical = item.badges.includes('critical');
  const meta = cardMeta(item);
  const importance = item.badges.find((b) => b === 'critical' || b === 'high');

  return (
    <div
      data-testid={`event-strip-card-${item.kind}-${item.symbol ?? 'na'}`}
      className={`w-40 flex-shrink-0 snap-start rounded-lg border p-2.5 ${
        isHoliday
          ? 'border-dashed border-gray-300 bg-transparent dark:border-gray-600'
          : isWatchEarnings
            ? 'border-[1.5px] border-indigo-400 bg-white dark:border-indigo-500 dark:bg-gray-800'
            : 'border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800'
      }`}
    >
      <div
        className={`text-[11px] font-bold tracking-wide ${
          isCritical ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400'
        }`}
      >
        {fmtDday(item.d_day)} · {item.event_date_et.slice(5).replace('-', '/')}
      </div>
      <div className="mt-0.5 flex items-center gap-1 text-[13px] font-medium text-gray-900 dark:text-gray-100">
        <span className="truncate">{item.title}</span>
        {item.session && (
          <span className="rounded border border-gray-200 px-1 text-[10px] text-gray-500 dark:border-gray-700 dark:text-gray-400">
            {item.session}
          </span>
        )}
      </div>
      {(meta || importance) && (
        <div className="mt-0.5 flex flex-wrap items-center gap-1 text-[11.5px] text-gray-400">
          {importance && (
            <span className={badgeClass(IMPORTANCE_BADGE_CLASS[importance])}>
              {importance.toUpperCase()}
            </span>
          )}
          {meta && <span>{meta}</span>}
        </div>
      )}
    </div>
  );
}

export function EventStrip() {
  const { data, isError } = useEventStrip();

  // 실패 격리: 에러·빈 응답·미도착 → 비표시(NewsStrip/MacroStrip 동형).
  if (isError || !data || data.items.length === 0) {
    return null;
  }

  const cards = sortAndCapTeasers(data.items);

  return (
    <section aria-label="이벤트 캘린더" className="w-full">
      <div className="mb-1 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
        <span className="h-2 w-2 rounded-full bg-teal-500" />
        <span>
          <b className="text-gray-800 dark:text-gray-100">다가오는 이벤트</b> · 45일 · 거시 HIGH
          이상 · 휴장 포함
        </span>
        <Link
          href="/monitor/calendar"
          className="ml-auto text-blue-600 hover:underline dark:text-blue-400"
        >
          캘린더 전체 →
        </Link>
      </div>
      <div
        role="list"
        className="flex gap-2 overflow-x-auto snap-x snap-mandatory pb-1"
      >
        {cards.map((item, idx) => (
          <div role="listitem" key={`${item.kind}-${item.symbol ?? 'x'}-${idx}`}>
            <EventCard item={item} />
          </div>
        ))}
      </div>
    </section>
  );
}
