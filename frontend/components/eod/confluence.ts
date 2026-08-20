// 스캐너 합류 모듈 (D-SCANNER-SELECT-UX ① · SCAN-B1-FE)
// 합류 정의 = **카테고리 축 단위**(원시 신호 개수 아님). 같은 카테고리를 여러
// 카드가 공유해도 1축으로 집계(가격 파생 신호 P1~P4 상관 중복 배제).
// tagger 6카테고리(momentum/volume/breakout/reversal/relation/technical)가 정본.
import type { SignalCategory, SignalCardDetail } from '@/types/eod';

export interface ConfluenceEntry {
  /** 이 종목이 걸린 서로 다른 카테고리 축(정렬·중복 배제). */
  categories: SignalCategory[];
  /** = categories.length (합류 축 수). */
  axisCount: number;
}

export type ConfluenceMap = Map<string, ConfluenceEntry>;

/** 배지 임계 = 2축 이상. (0.4 실측 분포: 2축+ 39% = 변별력 확보 · 퇴화 아님.) */
export const CONFLUENCE_MIN_AXES = 2;

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

/** map 미로딩(undefined) 안전 조회 — 없으면 0축(정칙 ⑴에서 칩 생략됨). */
export function getAxisCount(map: ConfluenceMap | undefined, symbol: string): number {
  return map?.get(symbol)?.axisCount ?? 0;
}
