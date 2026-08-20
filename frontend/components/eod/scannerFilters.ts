// 스캐너 필터·정렬 순수 로직 (D-SCANNER-SELECT-UX ③ · SCAN-B1-FE)
// 본판정·집계 무접촉 — 화면단 필터/정렬만. 백엔드 0.
import type { SignalStock, SortOption } from '@/types/eod';
import { getAxisCount, type ConfluenceMap } from './confluence';

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
 * (오늘 데이터는 전건 profile 폴백 → 실뉴스 0 → 뉴스 칩 자연 생략 = 정칙 ⑴.)
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

/** 선택 카드 종목에서 실제 등장하는 유효 섹터 목록(필터 드롭다운용·정렬). */
export function availableSectors(stocks: SignalStock[]): string[] {
  const set = new Set<string>();
  for (const s of stocks) if (validSector(s.sector)) set.add(s.sector);
  return [...set].sort();
}

/**
 * 정렬(원본 불변). 기존 3종은 카드 제공 rank 리스트 순서 유지, 합류순은 축 수 desc(동률 시 composite desc).
 */
export function sortScannerStocks(
  stocks: SignalStock[],
  sort: ScannerSort,
  map: ConfluenceMap | undefined,
  rankLists: { volume: string[]; return: string[]; market_cap: string[] },
): SignalStock[] {
  if (sort === 'confluence') {
    return [...stocks].sort((a, b) => {
      const ax = getAxisCount(map, a.symbol);
      const bx = getAxisCount(map, b.symbol);
      if (bx !== ax) return bx - ax;
      return b.composite_score - a.composite_score;
    });
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
