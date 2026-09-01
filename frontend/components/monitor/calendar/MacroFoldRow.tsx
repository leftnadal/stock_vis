// 거시 접힘 행 — EVT-4B STEP2(FE-TUNE-1 T2). 날짜 그룹(또는 "지난 7일 발표됨")의 거시
// 이벤트를 "거시 N건 ▸" 한 줄로 접고, CRITICAL 항목만 최대 3개 미리보기한다. 값의 진실은
// 여전히 BE 응답(EventItem) — 여기서는 표시 텍스트 조립 + 펼침 상태 토글만 한다
// (lib/monitor/calendarFormat.ts와 동일 원칙, 그 파일 자체는 이 STEP에서 무변).
import { formatTime } from '@/lib/monitor/calendarFormat';
import type { EventItem, MacroDetail } from '@/types/eventCalendar';

import { badgeClass, IMPORTANCE_BADGE_CLASS } from './eventColors';

const PREVIEW_LIMIT = 3;

function isCriticalMacro(item: EventItem): boolean {
  return item.badges.includes('critical');
}

function hasActualValue(item: EventItem): boolean {
  const d = item.detail as unknown as MacroDetail;
  return d.actual_value !== null && d.actual_value !== undefined && d.actual_value !== '';
}

function formatUpcomingPreview(item: EventItem): string {
  const time = formatTime(item);
  const timeText = [time.main, time.sub ? `(${time.sub})` : null].filter(Boolean).join(' ');
  return timeText ? `${item.title} ${timeText}` : item.title;
}

function formatPastPreview(item: EventItem): string {
  const d = item.detail as unknown as MacroDetail;
  return `${item.title} ${d.actual_value ?? ''} (예상 ${d.forecast_value ?? '—'})`;
}

interface MacroFoldRowProps {
  items: EventItem[]; // kind==='macro'인 항목만 전달받는다.
  open: boolean;
  onToggle: () => void;
  variant: 'upcoming' | 'past';
  testId: string;
}

export function MacroFoldRow({ items, open, onToggle, variant, testId }: MacroFoldRowProps) {
  if (items.length === 0) return null;

  const critical = items.filter(isCriticalMacro);
  let preview: string | null = null;

  if (variant === 'past') {
    const withActual = critical.filter(hasActualValue).slice(0, PREVIEW_LIMIT);
    if (withActual.length > 0) {
      preview = withActual.map(formatPastPreview).join(' · ');
    } else if (critical.length > 0) {
      preview = `실제값 미수신 ${critical.length}건`;
    }
  } else {
    const previewItems = critical.slice(0, PREVIEW_LIMIT);
    if (previewItems.length > 0) {
      preview = previewItems.map(formatUpcomingPreview).join(' · ');
    }
  }

  const countLabel = variant === 'past' ? `거시 ${items.length}건 발표` : `거시 ${items.length}건`;

  return (
    <button
      type="button"
      data-testid={testId}
      aria-expanded={open}
      onClick={onToggle}
      className="grid w-full grid-cols-[150px_1fr_200px_130px] items-center gap-2.5 border-b border-dashed border-gray-100 py-2 text-left last:border-0 dark:border-gray-800"
    >
      <div className="flex items-center gap-1.5 text-gray-700 dark:text-gray-200">
        <span aria-hidden="true" data-testid={`${testId}-caret`} className="text-gray-400">
          {open ? '▾' : '▸'}
        </span>
        <span className="text-sm font-medium">{countLabel}</span>
      </div>
      <div className="truncate text-xs text-gray-500 dark:text-gray-400" data-testid={`${testId}-preview`}>
        {preview && (
          <>
            <span className={badgeClass(IMPORTANCE_BADGE_CLASS.critical) + ' mr-1'}>CRITICAL</span>
            {preview}
          </>
        )}
      </div>
      <div />
      <div className="text-right text-xs text-gray-400">{open ? '접기' : '펼치기'}</div>
    </button>
  );
}
