'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchThemeHeatBar } from '@/services/chainsightService';
import type { ThemeHeatBarItem } from '@/types/chainsight';
import { bandColorClass } from './themeHeatCopy';

/** 점등(computed) 버튼 — 온도 + 밴드. */
function ComputedButton({ item, selected, onSelect }: { item: ThemeHeatBarItem; selected: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      data-testid={`computed-${item.theme}`}
      className={`flex flex-col items-start gap-0.5 rounded-lg border px-3 py-2 text-left transition-colors ${
        selected ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
      }`}
    >
      <span className="text-xs text-gray-600 dark:text-gray-300">{item.theme}</span>
      <span className="flex items-baseline gap-1">
        <span className={`text-lg font-bold ${bandColorClass(item.band)}`}>{item.score}</span>
        {item.delta_1d !== null && item.delta_1d !== 0 && (
          <span className="text-[10px] text-gray-400">{item.delta_1d > 0 ? '+' : ''}{item.delta_1d}</span>
        )}
      </span>
    </button>
  );
}

/** 미점등(accumulating) 진행바 — days/26 + D-n 조건부. */
function AccumulatingBar({ item, selected, onSelect }: { item: ThemeHeatBarItem; selected: boolean; onSelect: () => void }) {
  const pct = Math.min(100, Math.round((item.days / item.days_required) * 100));
  return (
    <button
      onClick={onSelect}
      data-testid={`accumulating-${item.theme}`}
      className={`flex flex-col items-start gap-1 rounded-lg border px-3 py-2 text-left w-full transition-colors ${
        selected ? 'border-blue-500' : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
      }`}
    >
      <span className="flex w-full items-center justify-between">
        <span className="text-xs text-gray-500">{item.theme}</span>
        <span className="text-[10px] text-gray-400">
          {item.days}/{item.days_required}
          {item.eta_days != null && <span> · D-{item.eta_days}</span>}
        </span>
      </span>
      <span className="h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
        <span className="block h-full rounded-full bg-gray-400" style={{ width: `${pct}%` }} />
      </span>
    </button>
  );
}

export default function ThemeHeatBar({ selected, onSelect }: { selected?: string; onSelect?: (theme: string) => void }) {
  const { data: items, isLoading, isError } = useQuery({
    queryKey: ['theme-heat-bar'],
    queryFn: fetchThemeHeatBar,
  });

  if (isLoading) return <div className="text-sm text-gray-400">불러오는 중…</div>;
  if (isError || !items) return <div className="text-sm text-red-500">버튼바를 불러오지 못했습니다.</div>;

  const computed = items.filter((i) => i.status === 'computed');
  const accumulating = items.filter((i) => i.status === 'accumulating');

  return (
    <div className="flex flex-col gap-3">
      {computed.length > 0 && (
        <div className="flex flex-wrap gap-2" data-testid="computed-group">
          {computed.map((i) => (
            <ComputedButton key={i.theme} item={i} selected={selected === i.theme} onSelect={() => onSelect?.(i.theme)} />
          ))}
        </div>
      )}
      {accumulating.length > 0 && (
        <div className="flex flex-col gap-2" data-testid="accumulating-group">
          <span className="text-[10px] uppercase tracking-wide text-gray-400">누적 중</span>
          {accumulating.map((i) => (
            <AccumulatingBar key={i.theme} item={i} selected={selected === i.theme} onSelect={() => onSelect?.(i.theme)} />
          ))}
        </div>
      )}
    </div>
  );
}
