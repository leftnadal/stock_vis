// 추천 카드 순수 로직 (DASH-RECO · SCAN-UX-2 R3/P3)
// composite_score는 301건 중 258건이 |1.0| 포화 → 순서·강도·신뢰 표시에 쓰지 않는다.
import type { Recommendation } from '@/types/eod';
import {
  compareConfluenceOrder,
  getAxisCount,
  type ConfluenceMap,
  type StockIndex,
} from './confluence';

/**
 * R3 정렬(원본 불변): 축 수 내림 → 거래대금 내림 → ticker 오름.
 * 거래대금은 추천 payload에 없으므로 카드 JSON(`stocks_by_score`) 조인값을 쓴다. 조인 실패 = 맨 뒤.
 */
export function sortRecommendations(
  recommendations: Recommendation[],
  map: ConfluenceMap | undefined,
  stockIndex: StockIndex | undefined,
): Recommendation[] {
  const key = (rec: Recommendation) => ({
    axes: getAxisCount(map, rec.ticker),
    dollarVolume: stockIndex?.get(rec.ticker)?.dollar_volume,
    symbol: rec.ticker,
  });
  return [...recommendations].sort((a, b) => compareConfluenceOrder(key(a), key(b)));
}

export type PerspectiveKind = 'fundamental' | 'technical' | 'news_context';

export const PERSPECTIVE_LABEL: Record<PerspectiveKind, string> = {
  technical: '기술',
  fundamental: '펀더멘털',
  news_context: '뉴스',
};

function present(text: string | null | undefined): string | null {
  return text && text.trim() ? text : null;
}

/** P3 관점 한 줄 = fundamental ?? technical. 둘 다 없으면 null(줄 생략 — "정보 없음" 표기 금지). */
export function pickPerspectiveLine(
  rec: Recommendation,
): { kind: PerspectiveKind; text: string } | null {
  const fundamental = present(rec.perspectives?.fundamental);
  if (fundamental) return { kind: 'fundamental', text: fundamental };
  const technical = present(rec.perspectives?.technical);
  if (technical) return { kind: 'technical', text: technical };
  return null;
}

/** 드로어 세 관점(기술·펀더·뉴스 순). 값 있는 관점만. */
export function presentPerspectives(
  rec: Recommendation,
): { kind: PerspectiveKind; text: string }[] {
  const order: PerspectiveKind[] = ['technical', 'fundamental', 'news_context'];
  return order.flatMap((kind) => {
    const text = present(rec.perspectives?.[kind]);
    return text ? [{ kind, text }] : [];
  });
}
