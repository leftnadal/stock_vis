// 스캐너 합류 모듈 (D-SCANNER-SELECT-UX ① · SCAN-B1-FE)
// 합류 정의 = **카테고리 축 단위**(원시 신호 개수 아님). 같은 카테고리를 여러
// 카드가 공유해도 1축으로 집계(가격 파생 신호 P1~P4 상관 중복 배제).
// tagger 6카테고리(momentum/volume/breakout/reversal/relation/technical)가 정본.
import type { SignalCategory, SignalCardDetail, SignalStock } from '@/types/eod';

export interface ConfluenceEntry {
  /** 이 종목이 걸린 서로 다른 카테고리 축(정렬·중복 배제). */
  categories: SignalCategory[];
  /** = categories.length (합류 축 수). */
  axisCount: number;
}

export type ConfluenceMap = Map<string, ConfluenceEntry>;

/** 배지 임계 = 2축 이상. (0.4 실측 분포: 2축+ 39% = 변별력 확보 · 퇴화 아님.) 스캐너 전용 — 추천 카드는 1축부터 표시(DASH-RECO R3). */
export const CONFLUENCE_MIN_AXES = 2;

/** 축 pips 표시 순서 = tagger 6카테고리 정본 순서(고정 칸 — 위치가 곧 축). */
export const AXIS_CATEGORIES: readonly SignalCategory[] = [
  'momentum', 'volume', 'breakout', 'reversal', 'relation', 'technical',
];

/** 종목 → 카드 JSON 행(체급·섹터·기술 조인용). 같은 종목이 여러 카드에 있으면 먼저 본 행. */
export type StockIndex = Map<string, SignalStock>;

type CardLike = Pick<SignalCardDetail, 'category' | 'stocks_by_score'>;

/**
 * 카드 전수 → 종목별 {카테고리 축 집합, 축 수} 지도.
 * 카테고리 중복 배제(Set)로 "원시 신호 개수"가 아닌 "직교 축 수"를 만든다.
 */
export function buildConfluenceMap(cards: CardLike[]): ConfluenceMap {
  const acc = new Map<string, Set<SignalCategory>>();
  for (const card of cards) {
    const cat = card.category;
    if (!cat) continue;
    for (const stock of card.stocks_by_score ?? []) {
      const sym = stock.symbol;
      if (!sym) continue;
      const set = acc.get(sym) ?? new Set<SignalCategory>();
      set.add(cat);
      acc.set(sym, set);
    }
  }
  const map: ConfluenceMap = new Map();
  for (const [sym, set] of acc) {
    const categories = [...set].sort() as SignalCategory[];
    map.set(sym, { categories, axisCount: categories.length });
  }
  return map;
}

/** 카드 전수 `stocks_by_score` → symbol 사전(추가 요청 0 — 합류 지도와 같은 카드 JSON 재사용). */
export function buildStockIndex(cards: CardLike[]): StockIndex {
  const index: StockIndex = new Map();
  for (const card of cards) {
    for (const stock of card.stocks_by_score ?? []) {
      if (stock?.symbol && !index.has(stock.symbol)) index.set(stock.symbol, stock);
    }
  }
  return index;
}

/** map 미로딩(undefined) 안전 조회 — 없으면 0축(정칙 ⑴에서 칩 생략됨). */
export function getAxisCount(map: ConfluenceMap | undefined, symbol: string): number {
  return map?.get(symbol)?.axisCount ?? 0;
}

/** map 미로딩(undefined) 안전 조회 — 걸린 카테고리 축(없으면 빈 배열). */
export function getAxisCategories(map: ConfluenceMap | undefined, symbol: string): SignalCategory[] {
  return map?.get(symbol)?.categories ?? [];
}

export interface ConfluenceOrderKey {
  axes: number;
  dollarVolume: number | null | undefined;
  symbol: string;
}

/**
 * 합류순 비교 — 추천 캐러셀(R3)과 스캐너 합류순(⑦-4)의 **단일 규칙**.
 * 축 수 내림 → 거래대금 내림(결측 = 맨 뒤) → symbol 오름.
 * (composite_score는 포화(|1.0|)라 동률 폴백으로 쓰지 않는다.)
 */
export function compareConfluenceOrder(a: ConfluenceOrderKey, b: ConfluenceOrderKey): number {
  if (b.axes !== a.axes) return b.axes - a.axes;
  const av = a.dollarVolume ?? -Infinity;
  const bv = b.dollarVolume ?? -Infinity;
  if (bv !== av) return bv > av ? 1 : -1;
  if (a.symbol === b.symbol) return 0;
  return a.symbol < b.symbol ? -1 : 1;
}
