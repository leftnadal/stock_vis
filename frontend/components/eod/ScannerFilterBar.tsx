'use client';

import {
  AXES_OPTS,
  DVOL_OPTS,
  MKTCAP_OPTS,
  type FilterOption,
  type ScannerFilters,
  type ScannerOptionCounts,
  type ScannerSort,
} from './scannerFilters';

/**
 * 스캐너 필터 바 (D-SCANNER-SELECT-UX ③ · SCAN-B1-FE · F5+F6 살아 있는 필터).
 * 로컬 상태(부모 소유) — URL 동기화는 후속 슬라이스. 본판정·집계 무접촉.
 * 정칙 ⑸: 거래대금 하한 필터 기본 제공.
 *
 * **F5+F6**: 임계 상수는 하나도 고치지 않는다. 각 옵션이 지금 몇 건을 남기는지 세서
 * ⑴ 라벨에 병기하고 ⑵ 아무것도 거르지 못하는 옵션은 그리지 않는다. 모집단이 바뀌면
 * 스스로 교정된다. 개수 집계는 `buildOptionCounts`(부모의 useMemo)가 넘겨준다.
 */
const SORT_OPTS: { label: string; value: ScannerSort }[] = [
  { label: '합류순', value: 'confluence' },
  { label: '거래량순', value: 'volume' },
  { label: '수익률순', value: 'return' },
  { label: '시가총액순', value: 'market_cap' },
];

const selectClass =
  'rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-[11px] text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400';

/** 한 `<option>`의 표시 판정. */
interface OptionView<V> {
  value: V;
  label: string;
  count: number;
  disabled: boolean;
}

/**
 * 옵션 목록 → 실제로 그릴 목록.
 *
 * - `전체`(value 0/'')는 **항상 남긴다** — 해제 수단이 사라지면 안 된다.
 * - **현재 선택된 옵션은 절대 숨기지 않는다.** `<select>`의 `value`에 해당하는
 *   `<option>`이 DOM에 없으면 브라우저가 첫 옵션을 보여주는데 상태는 그대로다 —
 *   화면과 상태가 갈라진다. 칩과 달리 `<select>`에서는 이게 치명적이다.
 * - 결과가 `base`와 같은 옵션(= 아무것도 못 거름)은 그리지 않는다.
 * - 결과 0은 **숨기지 않고** `disabled` + `(0)`. "거르지 못함"과 반대이고 0은 그 자체로 정보다.
 */
export function visibleOptions<V extends string | number>(
  opts: FilterOption<V>[],
  counts: Record<string, number>,
  base: number,
  current: V,
  allValue: V,
): OptionView<V>[] {
  const out: OptionView<V>[] = [];
  for (const o of opts) {
    const count = counts[String(o.value)] ?? 0;
    const isAll = o.value === allValue;
    const isCurrent = o.value === current;
    if (!isAll && !isCurrent && count === base) continue; // 아무것도 못 거름 → 미렌더
    out.push({ value: o.value, label: o.label, count, disabled: count === 0 && !isCurrent });
  }
  return out;
}

/** 전체/현재선택 말고 실효 옵션이 하나라도 남았는가. 없으면 `<select>`를 통째로 감춘다(정칙 ⑴). */
export function hasLiveOption<V extends string | number>(
  views: OptionView<V>[],
  allValue: V,
  current: V,
): boolean {
  return views.some((v) => v.value !== allValue || v.value === current) && views.length > 1;
}

interface Props {
  filters: ScannerFilters;
  onFiltersChange: (next: ScannerFilters) => void;
  sort: ScannerSort;
  onSortChange: (sort: ScannerSort) => void;
  sectors: string[];
  resultCount: number;
  totalCount: number;
  /** 옵션별 잔여 수(F5+F6). 미지정이면 개수 병기·죽은 옵션 숨김 없이 종전대로 그린다. */
  optionCounts?: ScannerOptionCounts;
}

export function ScannerFilterBar({
  filters,
  onFiltersChange,
  sort,
  onSortChange,
  sectors,
  resultCount,
  totalCount,
  optionCounts,
}: Props) {
  const set = (patch: Partial<ScannerFilters>) => onFiltersChange({ ...filters, ...patch });

  const sectorOpts: FilterOption<string>[] = [
    { label: '섹터 전체', value: '' },
    ...sectors.map((s) => ({ label: s, value: s })),
  ];

  // optionCounts 부재(테스트·구버전 호출부) = 전량 표시 + 개수 미병기.
  const views = optionCounts
    ? {
        sector: visibleOptions(sectorOpts, optionCounts.sector, optionCounts.base, filters.sector ?? '', ''),
        mktcap: visibleOptions(MKTCAP_OPTS, optionCounts.marketCapMin, optionCounts.base, filters.marketCapMin, 0),
        dvol: visibleOptions(DVOL_OPTS, optionCounts.dollarVolumeMin, optionCounts.base, filters.dollarVolumeMin, 0),
        axes: visibleOptions(AXES_OPTS, optionCounts.minAxes, optionCounts.base, filters.minAxes, 0),
      }
    : null;

  const renderSelect = <V extends string | number>(
    ariaLabel: string,
    value: V,
    onChange: (raw: string) => void,
    fallback: FilterOption<V>[],
    view: OptionView<V>[] | undefined,
    allValue: V,
  ) => {
    if (view && !hasLiveOption(view, allValue, value)) return null; // 축 전체가 죽음 → 통째 미렌더
    const items = view ?? fallback.map((o) => ({ ...o, count: -1, disabled: false }));
    return (
      <select
        aria-label={ariaLabel}
        className={selectClass}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {items.map((o) => (
          <option key={String(o.value)} value={o.value} disabled={o.disabled}>
            {o.count >= 0 ? `${o.label} (${o.count})` : o.label}
          </option>
        ))}
      </select>
    );
  };

  // 뉴스 버튼: 아무것도 못 거르면 숨긴다 — 단 켜져 있으면 숨기지 않는다(해제 수단 보존).
  const newsCount = optionCounts?.newsOnly;
  const showNews =
    optionCounts == null || filters.newsOnly || newsCount !== optionCounts.base;

  return (
    <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0 bg-gray-50/60 dark:bg-gray-800/40">
      <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="스캐너 필터">
        {renderSelect<string>(
          '섹터 필터',
          filters.sector ?? '',
          (raw) => set({ sector: raw || null }),
          sectorOpts,
          views?.sector,
          '',
        )}

        {renderSelect<number>(
          '시가총액 하한',
          filters.marketCapMin,
          (raw) => set({ marketCapMin: Number(raw) }),
          MKTCAP_OPTS,
          views?.mktcap,
          0,
        )}

        {renderSelect<number>(
          '거래대금 하한',
          filters.dollarVolumeMin,
          (raw) => set({ dollarVolumeMin: Number(raw) }),
          DVOL_OPTS,
          views?.dvol,
          0,
        )}

        {renderSelect<number>(
          '합류 축 필터',
          filters.minAxes,
          (raw) => set({ minAxes: Number(raw) }),
          AXES_OPTS,
          views?.axes,
          0,
        )}

        {showNews && (
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
            {newsCount != null ? `뉴스 있음 (${newsCount})` : '뉴스 있음'}
          </button>
        )}

        {/* 정렬은 목록을 줄이지 않으므로 개수 개념이 없다 — 무변경. */}
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
