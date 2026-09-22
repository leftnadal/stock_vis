// 스캐너 필터·정렬 순수 로직 (D-SCANNER-SELECT-UX ③ · SCAN-B1-FE)
// 본판정·집계 무접촉 — 화면단 필터/정렬만. 백엔드 0.
import type { SignalStock, SortOption } from '@/types/eod';
import { compareConfluenceOrder, getAxisCount, type ConfluenceMap } from './confluence';

/** 정렬 옵션 = 기존 3종 + 합류순. */
export type ScannerSort = SortOption | 'confluence';

export interface ScannerFilters {
  /** null = 전체. */
  sector: string | null;
  /** 시총 하한($). 0 = 무제한. */
  marketCapMin: number;
  /** 거래대금 하한($). 0 = 무제한. (정칙 ⑸ — 필터에 거래대금 하한 기본 제공.) */
  dollarVolumeMin: number;
  /** 합류 N축 이상. 0 = 무필터. */
  minAxes: number;
  /** true = 실매칭 뉴스 보유 종목만. */
  newsOnly: boolean;
}

export const DEFAULT_SCANNER_FILTERS: ScannerFilters = {
  sector: null,
  marketCapMin: 0,
  dollarVolumeMin: 0,
  minAxes: 0,
  newsOnly: false,
};

const INVALID_SECTORS = new Set(['', 'Unknown', 'N/A']);

/** 유효 섹터(칩·필터 표기 대상). 결측/Unknown = false → 정칙 ⑴ 생략. */
export function validSector(sector: string | null | undefined): boolean {
  return !!sector && !INVALID_SECTORS.has(sector);
}

/**
 * 실매칭 뉴스 여부. match_type === 'profile'(프로필 폴백) 또는 headline 부재 = 뉴스 아님.
 * 09-03 sync·bake 이후 news_context는 실뉴스 매칭(symbol_today·symbol_7d)이 대부분이라
 * `뉴스만` 필터는 실제로 걸러낸다. (예전 "전건 profile 폴백 → 실뉴스 0" 주석은 #128 시절 사실 — 폐기.)
 */
export function hasRealNews(stock: SignalStock): boolean {
  const nc = stock.news_context;
  return !!nc?.headline && nc.match_type !== 'profile';
}

/** 뉴스 신선도 서술(정칙 ⑵ — 감성 주장 아님, 상태 서술만). */
export function newsRecencyLabel(stock: SignalStock): string {
  const nc = stock.news_context;
  if (!nc) return '뉴스';
  if (nc.match_type === 'symbol_today' || nc.age_days === 0) return '뉴스 · 오늘';
  if (nc.match_type === 'industry_7d') return '업종 뉴스';
  if (nc.age_days > 0) return `뉴스 · ${nc.age_days}일 전`;
  return '뉴스';
}

/** 필터 적용(원본 불변). */
export function applyScannerFilters(
  stocks: SignalStock[],
  filters: ScannerFilters,
  map: ConfluenceMap | undefined,
): SignalStock[] {
  return stocks.filter((s) => {
    if (filters.sector && s.sector !== filters.sector) return false;
    if (filters.marketCapMin > 0 && (s.market_cap ?? 0) < filters.marketCapMin) return false;
    if (filters.dollarVolumeMin > 0 && (s.dollar_volume ?? 0) < filters.dollarVolumeMin) return false;
    if (filters.minAxes > 0 && getAxisCount(map, s.symbol) < filters.minAxes) return false;
    if (filters.newsOnly && !hasRealNews(s)) return false;
    return true;
  });
}

// ── 필터 옵션 카탈로그 (F5+F6) ──────────────────────────────────────────────
// ⚠ `value`(임계 상수)는 **불변**이다. 살아 있는 필터는 임계를 고치는 게 아니라
//   "이 옵션이 지금 몇 건을 거르는가"를 세서 라벨에 붙이고 죽은 옵션을 감출 뿐이다.
//   ScannerFilterBar(표시)와 countByOption(집계)이 같은 목록을 보게 하려고 여기 둔다.

export interface FilterOption<V> {
  label: string;
  value: V;
}

export const MKTCAP_OPTS: FilterOption<number>[] = [
  { label: '시총 전체', value: 0 },
  { label: '$1B+', value: 1_000_000_000 },
  { label: '$10B+', value: 10_000_000_000 },
  { label: '$50B+', value: 50_000_000_000 },
];
export const DVOL_OPTS: FilterOption<number>[] = [
  { label: '거래대금 전체', value: 0 },
  { label: '$1M+', value: 1_000_000 },
  { label: '$10M+', value: 10_000_000 },
  { label: '$50M+', value: 50_000_000 },
];
export const AXES_OPTS: FilterOption<number>[] = [
  { label: '합류 전체', value: 0 },
  { label: '2축+', value: 2 },
  { label: '3축+', value: 3 },
];

/**
 * 한 축의 값을 `value`로 **바꿔** 적용했을 때 남는 종목 수.
 *
 * **다른 축의 현재 선택은 유지한다** = "지금 상태에서 이걸 *더* 걸면 몇 개".
 * 전체 목록 기준으로 세면 숫자는 안정적이지만 눌렀을 때 예상과 어긋난다 —
 * 필터의 목적이 좁히기이므로 현재 상태 기준이 맞다.
 *
 * ⚠ `applyScannerFilters`를 **그대로 재사용**한다. 세는 규칙과 거르는 규칙이
 *   어긋날 수 없게 하는 것이 이 함수의 요점이다. 판정식을 복제하면 값어치가 사라진다.
 */
export function countByOption<K extends keyof ScannerFilters>(
  stocks: SignalStock[],
  filters: ScannerFilters,
  map: ConfluenceMap | undefined,
  axis: K,
  value: ScannerFilters[K],
): number {
  return applyScannerFilters(stocks, { ...filters, [axis]: value }, map).length;
}

/** 옵션별 잔여 수 전수. `base` = 현재 필터 결과 수(= 아무것도 안 거르는 옵션의 기준선). */
export interface ScannerOptionCounts {
  base: number;
  marketCapMin: Record<number, number>;
  dollarVolumeMin: Record<number, number>;
  minAxes: Record<number, number>;
  /** 키 '' = 섹터 전체(null). */
  sector: Record<string, number>;
  /** newsOnly=true 를 적용했을 때 남는 수. */
  newsOnly: number;
}

/** 표시 계층이 쓸 개수 전수 집계. 호출부에서 useMemo 한 겹으로 감싼다. */
export function buildOptionCounts(
  stocks: SignalStock[],
  filters: ScannerFilters,
  map: ConfluenceMap | undefined,
  sectors: string[],
): ScannerOptionCounts {
  const countAxis = <K extends keyof ScannerFilters>(
    axis: K,
    values: ScannerFilters[K][],
  ): Record<string, number> => {
    const out: Record<string, number> = {};
    for (const v of values) out[String(v)] = countByOption(stocks, filters, map, axis, v);
    return out;
  };

  return {
    base: applyScannerFilters(stocks, filters, map).length,
    marketCapMin: countAxis('marketCapMin', MKTCAP_OPTS.map((o) => o.value)),
    dollarVolumeMin: countAxis('dollarVolumeMin', DVOL_OPTS.map((o) => o.value)),
    minAxes: countAxis('minAxes', AXES_OPTS.map((o) => o.value)),
    sector: {
      '': countByOption(stocks, filters, map, 'sector', null),
      ...Object.fromEntries(
        sectors.map((sec) => [sec, countByOption(stocks, filters, map, 'sector', sec)]),
      ),
    },
    newsOnly: countByOption(stocks, filters, map, 'newsOnly', true),
  };
}

/** 선택 카드 종목에서 실제 등장하는 유효 섹터 목록(필터 드롭다운용·정렬). */
export function availableSectors(stocks: SignalStock[]): string[] {
  const set = new Set<string>();
  for (const s of stocks) if (validSector(s.sector)) set.add(s.sector);
  return [...set].sort();
}

/**
 * 정렬(원본 불변). 기존 3종은 카드 제공 rank 리스트 순서 유지.
 * 합류순 = 추천 캐러셀과 같은 규칙(compareConfluenceOrder: 축 수 → 거래대금 → symbol).
 */
export function sortScannerStocks(
  stocks: SignalStock[],
  sort: ScannerSort,
  map: ConfluenceMap | undefined,
  rankLists: { volume: string[]; return: string[]; market_cap: string[] },
): SignalStock[] {
  if (sort === 'confluence') {
    return [...stocks].sort((a, b) =>
      compareConfluenceOrder(
        { axes: getAxisCount(map, a.symbol), dollarVolume: a.dollar_volume, symbol: a.symbol },
        { axes: getAxisCount(map, b.symbol), dollarVolume: b.dollar_volume, symbol: b.symbol },
      ),
    );
  }
  const rankList = rankLists[sort];
  if (!rankList || rankList.length === 0) return stocks;
  const rankMap = new Map(rankList.map((sym, idx) => [sym, idx]));
  return [...stocks].sort((a, b) => {
    const ra = rankMap.has(a.symbol) ? rankMap.get(a.symbol)! : 9999;
    const rb = rankMap.has(b.symbol) ? rankMap.get(b.symbol)! : 9999;
    return ra - rb;
  });
}
