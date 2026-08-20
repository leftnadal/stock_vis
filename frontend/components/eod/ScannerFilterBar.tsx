'use client';

import type { ScannerFilters, ScannerSort } from './scannerFilters';

/**
 * 스캐너 필터 바 (D-SCANNER-SELECT-UX ③ · SCAN-B1-FE).
 * 로컬 상태(부모 소유) — URL 동기화는 후속 슬라이스. 본판정·집계 무접촉.
 * 정칙 ⑸: 거래대금 하한 필터 기본 제공.
 */
const MKTCAP_OPTS: { label: string; value: number }[] = [
  { label: '시총 전체', value: 0 },
  { label: '$1B+', value: 1_000_000_000 },
  { label: '$10B+', value: 10_000_000_000 },
  { label: '$50B+', value: 50_000_000_000 },
];
const DVOL_OPTS: { label: string; value: number }[] = [
  { label: '거래대금 전체', value: 0 },
  { label: '$1M+', value: 1_000_000 },
  { label: '$10M+', value: 10_000_000 },
  { label: '$50M+', value: 50_000_000 },
];
const AXES_OPTS: { label: string; value: number }[] = [
  { label: '합류 전체', value: 0 },
  { label: '2축+', value: 2 },
  { label: '3축+', value: 3 },
];
const SORT_OPTS: { label: string; value: ScannerSort }[] = [
  { label: '합류순', value: 'confluence' },
  { label: '거래량순', value: 'volume' },
  { label: '수익률순', value: 'return' },
  { label: '시가총액순', value: 'market_cap' },
];

const selectClass =
  'rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-[11px] text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400';

interface Props {
  filters: ScannerFilters;
  onFiltersChange: (next: ScannerFilters) => void;
  sort: ScannerSort;
  onSortChange: (sort: ScannerSort) => void;
  sectors: string[];
  resultCount: number;
  totalCount: number;
}

export function ScannerFilterBar({
  filters,
  onFiltersChange,
  sort,
  onSortChange,
  sectors,
  resultCount,
  totalCount,
}: Props) {
  const set = (patch: Partial<ScannerFilters>) => onFiltersChange({ ...filters, ...patch });

  return (
    <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0 bg-gray-50/60 dark:bg-gray-800/40">
      <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="스캐너 필터">
        <select
          aria-label="섹터 필터"
          className={selectClass}
          value={filters.sector ?? ''}
          onChange={(e) => set({ sector: e.target.value || null })}
        >
          <option value="">섹터 전체</option>
          {sectors.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <select
          aria-label="시가총액 하한"
          className={selectClass}
          value={filters.marketCapMin}
          onChange={(e) => set({ marketCapMin: Number(e.target.value) })}
        >
          {MKTCAP_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <select
          aria-label="거래대금 하한"
          className={selectClass}
          value={filters.dollarVolumeMin}
          onChange={(e) => set({ dollarVolumeMin: Number(e.target.value) })}
        >
          {DVOL_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <select
          aria-label="합류 축 필터"
          className={selectClass}
          value={filters.minAxes}
          onChange={(e) => set({ minAxes: Number(e.target.value) })}
        >
          {AXES_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <button
          type="button"
          aria-pressed={filters.newsOnly}
          onClick={() => set({ newsOnly: !filters.newsOnly })}
          className={`rounded-md border px-2 py-1 text-[11px] font-medium transition-colors ${
            filters.newsOnly
              ? 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800'
              : 'bg-white text-gray-500 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-600'
          }`}
        >
          뉴스 있음
        </button>

        <select
          aria-label="정렬"
          className={`${selectClass} ml-auto`}
          value={sort}
          onChange={(e) => onSortChange(e.target.value as ScannerSort)}
        >
          {SORT_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
      <p className="mt-1 text-[10px] text-gray-400 dark:text-gray-500">
        {resultCount}/{totalCount}종목
      </p>
    </div>
  );
}
