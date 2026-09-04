// 다가오는 이벤트 한 줄 pill 밴드 (EVT-CHAIN-1B / P1). 상태 카드 바로 아래 附加.
// 어닝·배당 pill + "관계망 N ↓" pill(클릭 → 하단 타임라인 앵커 스크롤). 이벤트 없으면 밴드 비표시.
// useChainFeed는 ChainSection과 동일 키 → TanStack 캐시 공유(중복 fetch 없음). 부호 중립.
'use client';

import { badgeClass, KIND_BADGE_CLASS, KIND_LABEL } from '@/components/monitor/calendar/eventColors';
import { fmtDateShort, fmtDday, formatDetail } from '@/lib/monitor/calendarFormat';
import { useChainFeed } from '@/hooks/useEventCalendar';
import { CHAIN_TIMELINE_ANCHOR } from './ChainSection';

const PILL =
  'inline-flex items-center gap-1.5 rounded-md border border-gray-200 px-2.5 py-1 text-xs dark:border-gray-700';

interface Props {
  symbol: string;
}

export function UpcomingEventsBand({ symbol }: Props) {
  const { data, isError } = useChainFeed(symbol, true);
  if (isError || !data) return null;

  const nextEarn = data.seed_events.find((e) => e.kind === 'earnings');
  const nextDiv = data.seed_events.find((e) => e.kind === 'dividend');
  const nbrCount = data.neighbors.length;
  // 이벤트 없으면(어닝·배당·이웃 전무) 밴드 자체 비표시.
  if (!nextEarn && !nextDiv && nbrCount === 0) return null;

  const scrollToTimeline = () => {
    document.getElementById(CHAIN_TIMELINE_ANCHOR)?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
  };

  return (
    <div
      data-testid="upcoming-band"
      className="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 dark:border-gray-800 dark:bg-gray-900"
    >
      <span className="text-[11px] text-gray-400">다가오는 이벤트</span>
      {nextEarn && (
        <span data-testid="band-earnings-pill" className={PILL}>
          <span className={badgeClass(KIND_BADGE_CLASS.earnings)}>{KIND_LABEL.earnings}</span>
          <span className="font-mono font-bold text-blue-600 dark:text-blue-400">
            {fmtDday(nextEarn.d_day)}
          </span>
          <span className="text-gray-500 dark:text-gray-400">{fmtDateShort(nextEarn.event_date_et)}</span>
          <span className="text-gray-600 dark:text-gray-300">· {formatDetail(nextEarn)}</span>
        </span>
      )}
      {nextDiv && (
        <span data-testid="band-dividend-pill" className={PILL}>
          <span className={badgeClass(KIND_BADGE_CLASS.dividend)}>{KIND_LABEL.dividend}</span>
          <span className="font-mono font-bold text-blue-600 dark:text-blue-400">
            {fmtDday(nextDiv.d_day)}
          </span>
          <span className="text-gray-500 dark:text-gray-400">{fmtDateShort(nextDiv.event_date_et)}</span>
        </span>
      )}
      {nbrCount > 0 && (
        <button
          type="button"
          data-testid="chain-anchor-pill"
          onClick={scrollToTimeline}
          className={`${PILL} cursor-pointer hover:border-teal-300 hover:bg-teal-50 dark:hover:bg-teal-900/20`}
        >
          <span className={badgeClass('bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300')}>
            관계망 {nbrCount}
          </span>
          <span className="text-blue-600 dark:text-blue-400">↓</span>
        </button>
      )}
    </div>
  );
}
