'use client';

// 이벤트 캘린더 페이지 (EVT-IMPL-4 STEP 3) — 관심종목(모니터∪관심목록) 어닝·배당락·분할·
// 거시·휴장 연합 읽기. 시각 계약: docs/design/evt_phase1_mockups.html Screen A.
import { useMemo, useState } from 'react';

import Link from 'next/link';

import { AuthGuard } from '@/components/auth/AuthGuard';
import { DateGroup } from '@/components/monitor/calendar/DateGroup';
import { EventRow } from '@/components/monitor/calendar/EventRow';
import { ScopeChips } from '@/components/monitor/calendar/ScopeChips';
import { useEventCalendar } from '@/hooks/useEventCalendar';
import type { EventFeed, EventItem, EventKind, EventScope } from '@/types/eventCalendar';

type KindFilter = 'all' | 'earnings' | 'dividend' | 'split' | 'macro' | 'holiday';

const KIND_CHIPS: { key: KindFilter; label: string; kinds: EventKind[] }[] = [
  { key: 'all', label: '전체', kinds: [] },
  { key: 'earnings', label: '어닝', kinds: ['earnings'] },
  { key: 'dividend', label: '배당락', kinds: ['dividend'] },
  { key: 'split', label: '분할', kinds: ['split', 'split_effective'] },
  { key: 'macro', label: '거시', kinds: ['macro'] },
  { key: 'holiday', label: '휴장', kinds: ['holiday'] },
];

function chipCount(counts: EventFeed['counts'], kinds: EventKind[]): number {
  if (kinds.length === 0) {
    return Object.values(counts).reduce((sum: number, n) => sum + (n ?? 0), 0);
  }
  return kinds.reduce((sum, k) => sum + (counts[k] ?? 0), 0);
}

function activeSymbolCount(data: EventFeed, scope: EventScope): number {
  if (scope === 'monitor') return data.symbols.monitor.length;
  if (scope === 'watchlist') return data.symbols.watchlist.length;
  return new Set([...data.symbols.monitor, ...data.symbols.watchlist]).size;
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-gray-300 py-16 text-center dark:border-gray-700">
      <p className="text-4xl">📅</p>
      <p className="font-medium text-gray-800 dark:text-gray-100">관심종목이 없습니다</p>
      <div className="flex gap-3 text-sm">
        <Link href="/monitor/new" className="text-blue-600 hover:underline dark:text-blue-400">
          모니터 만들기
        </Link>
        <span className="text-gray-300 dark:text-gray-600">/</span>
        <Link href="/watchlist" className="text-blue-600 hover:underline dark:text-blue-400">
          관심목록
        </Link>
      </div>
    </div>
  );
}

function CalendarContent() {
  const [scope, setScope] = useState<EventScope>('monitor');
  const [kindFilter, setKindFilter] = useState<KindFilter>('all');
  const [showStale, setShowStale] = useState(false);

  const { data, isLoading, isError } = useEventCalendar({ scope });

  const visibleItems = useMemo(() => {
    if (!data) return [];
    const activeKinds = KIND_CHIPS.find((c) => c.key === kindFilter)?.kinds ?? [];
    return data.items.filter((item: EventItem) => {
      if (activeKinds.length > 0 && !activeKinds.includes(item.kind)) return false;
      if (!showStale && item.status === 'stale') return false;
      return true;
    });
  }, [data, kindFilter, showStale]);

  const todayEt = data?.as_of.slice(0, 10) ?? null;

  const pastItems = useMemo(
    () => (todayEt ? visibleItems.filter((item) => item.event_date_et < todayEt) : []),
    [visibleItems, todayEt],
  );

  const dateGroups = useMemo(() => {
    if (!todayEt) return [] as Array<[string, EventItem[]]>;
    const map = new Map<string, EventItem[]>();
    for (const item of visibleItems) {
      if (item.event_date_et < todayEt) continue;
      const list = map.get(item.event_date_et) ?? [];
      list.push(item);
      map.set(item.event_date_et, list);
    }
    return [...map.entries()];
  }, [visibleItems, todayEt]);

  const isEmpty = !!data && activeSymbolCount(data, scope) === 0;

  // data-guide 앵커는 가이드 콘텐츠 슬라이스에서만 부여(orphan 금지) — EVT-IMPL-4 STEP4 디렉터 처분.
  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">이벤트 캘린더</h1>
          <p className="text-sm text-gray-500" data-testid="calendar-header-sub">
            관심종목 {data ? activeSymbolCount(data, scope) : 0} · ET 기준, KST 병기
          </p>
        </div>
        {data && (
          <p className="text-xs text-gray-400" data-testid="as-of">
            기준 {data.as_of.slice(0, 10)} · {data.as_of.slice(11, 16)} ET 갱신
          </p>
        )}
      </div>

      {isLoading && <p className="py-12 text-center text-gray-400">불러오는 중…</p>}
      {isError && <p className="py-12 text-center text-red-500">캘린더를 불러오지 못했어요.</p>}

      {!isLoading && !isError && data && (
        <>
          <div className="mb-2 flex flex-wrap gap-2" data-testid="kind-chips">
            {KIND_CHIPS.map((c) => (
              <button
                key={c.key}
                type="button"
                data-testid={`kind-chip-${c.key}`}
                aria-pressed={kindFilter === c.key}
                onClick={() => setKindFilter(c.key)}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-sm transition ${
                  kindFilter === c.key
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
                }`}
              >
                {c.label}
                <span className={kindFilter === c.key ? 'text-blue-100' : 'text-gray-400'}>
                  {chipCount(data.counts, c.kinds)}
                </span>
              </button>
            ))}
          </div>

          <ScopeChips value={scope} onChange={setScope} />

          <label className="mb-3 flex w-fit items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <input
              type="checkbox"
              data-testid="stale-toggle"
              checked={showStale}
              onChange={(e) => setShowStale(e.target.checked)}
              className="h-3.5 w-3.5"
            />
            stale 표시 (소실된 일정 포함)
          </label>

          {isEmpty && <EmptyState />}

          {!isEmpty && (
            <>
              {pastItems.length > 0 && (
                <div data-testid="past-section">
                  <div className="mb-1.5 flex items-baseline gap-2 border-b border-gray-200 pb-1 text-xs text-gray-400 dark:border-gray-700">
                    <span className="font-bold text-gray-800 dark:text-gray-100">
                      지난 7일 발표됨
                    </span>
                    <span>· 서프라이즈 = (실제 − 예상) / |예상|</span>
                  </div>
                  <div className="flex flex-col">
                    {pastItems.map((item, idx) => (
                      <EventRow key={`past-${item.kind}-${item.symbol ?? 'x'}-${idx}`} item={item} />
                    ))}
                  </div>
                </div>
              )}

              {dateGroups.map(([date, items]) => (
                <DateGroup key={date} date={date} items={items} />
              ))}

              {pastItems.length === 0 && dateGroups.length === 0 && (
                <p className="py-8 text-center text-sm text-gray-400">
                  이 필터에 해당하는 이벤트가 없어요.
                </p>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

export default function EventCalendarPage() {
  return (
    <AuthGuard>
      <CalendarContent />
    </AuthGuard>
  );
}
