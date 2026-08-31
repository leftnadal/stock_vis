// 범위 칩(D-EVT-4A A3 채택 — 모니터 종목 / 관심목록 / 둘 다). 기본값=모니터 종목.
// scope 전환은 서버 필터(계약 §엔드포인트 scope 파라미터) → onChange가 refetch를 유발한다.
'use client';

import type { EventScope } from '@/types/eventCalendar';

const OPTIONS: { key: EventScope; label: string }[] = [
  { key: 'monitor', label: '모니터 종목' },
  { key: 'watchlist', label: '관심목록' },
  { key: 'both', label: '둘 다' },
];

interface ScopeChipsProps {
  value: EventScope;
  onChange: (scope: EventScope) => void;
}

export function ScopeChips({ value, onChange }: ScopeChipsProps) {
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2" data-testid="scope-chips">
      <span className="text-[11px] tracking-wide text-gray-400">범위</span>
      {OPTIONS.map((opt) => (
        <button
          key={opt.key}
          type="button"
          data-testid={`scope-chip-${opt.key}`}
          aria-pressed={value === opt.key}
          onClick={() => onChange(opt.key)}
          className={`rounded-full border px-3 py-1 text-sm transition ${
            value === opt.key
              ? 'border-transparent bg-blue-600 text-white'
              : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
