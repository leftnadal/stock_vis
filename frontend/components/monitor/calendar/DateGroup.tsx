// 날짜 그룹 — 그룹헤더(날짜·요일·D-day) + 그 날짜의 행 목록(휴장 인터리브 포함).
import { format, parseISO } from 'date-fns';
import { ko } from 'date-fns/locale';

import { EventRow } from './EventRow';
import { fmtDday } from '@/lib/monitor/calendarFormat';
import type { EventItem } from '@/types/eventCalendar';

interface DateGroupProps {
  date: string; // YYYY-MM-DD (ET)
  items: EventItem[];
}

export function DateGroup({ date, items }: DateGroupProps) {
  if (items.length === 0) return null;
  const dDay = items[0].d_day;
  const isToday = dDay === 0;
  const label = format(parseISO(date), 'M월 d일 (EEEEEE)', { locale: ko });

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
        {items.map((item, idx) => (
          <EventRow key={`${date}-${item.kind}-${item.symbol ?? 'x'}-${idx}`} item={item} />
        ))}
      </div>
    </div>
  );
}
