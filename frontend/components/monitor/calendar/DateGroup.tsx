// 날짜 그룹 — 그룹헤더(날짜·요일·D-day) + 그 날짜의 행 목록(휴장 인터리브 포함).
// EVT-4B STEP2(FE-TUNE-1 T2): 관심종목 이벤트(어닝·배당·분할)·휴장은 항상 펼치고,
// 거시는 MacroFoldRow 한 줄로 접는다(펼침 상태는 상위 페이지가 소유 — 전역 토글 때문).
import { format, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';

import { EventRow } from './EventRow';
import { MacroFoldRow } from './MacroFoldRow';
import { fmtDday } from '@/lib/monitor/calendarFormat';
import type { EventItem, EventKind } from '@/types/eventCalendar';

const ALWAYS_VISIBLE_KINDS: EventKind[] = ['earnings', 'dividend', 'split', 'split_effective', 'holiday'];

interface DateGroupProps {
  date: string; // YYYY-MM-DD (ET)
  items: EventItem[];
  macroOpen: boolean;
  onToggleMacro: () => void;
}

export function DateGroup({ date, items, macroOpen, onToggleMacro }: DateGroupProps) {
  if (items.length === 0) return null;
  const dDay = items[0].d_day;
  const isToday = dDay === 0;
  const label = format(parseISO(date), 'M월 d일 (EEEEEE)', { locale: ko });

  const visibleItems = items.filter((item) => ALWAYS_VISIBLE_KINDS.includes(item.kind));
  const macroItems = items.filter((item) => item.kind === 'macro');

  return (
    <div className="mt-4" data-testid={`date-group-${date}`}>
      <div className="mb-1.5 flex items-baseline gap-2 border-b border-gray-200 pb-1 dark:border-gray-700">
        <span className="text-sm font-bold text-gray-800 dark:text-gray-100">{label}</span>
        <span
          data-testid="date-group-dday"
          className={`text-xs font-medium ${
            isToday ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400'
          }`}
        >
          {fmtDday(dDay)}
        </span>
      </div>
      <div className="flex flex-col">
        {visibleItems.map((item, idx) => (
          <EventRow key={`${date}-${item.kind}-${item.symbol ?? 'x'}-${idx}`} item={item} />
        ))}
        {macroOpen
          ? macroItems.map((item, idx) => (
              <EventRow key={`${date}-macro-${item.symbol ?? 'x'}-${idx}`} item={item} />
            ))
          : (
            <MacroFoldRow
              items={macroItems}
              open={macroOpen}
              onToggle={onToggleMacro}
              variant="upcoming"
              testId={`macro-fold-${date}`}
            />
          )}
      </div>
    </div>
  );
}
