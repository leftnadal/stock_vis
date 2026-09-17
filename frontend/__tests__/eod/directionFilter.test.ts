import { describe, it, expect } from 'vitest';
import {
  countDirections,
  countUniqueSymbols,
  directionOfScore,
  filterCardsByDirection,
} from '@/components/eod/MarketSummaryBar';
import type { SignalCard, SignalStock } from '@/types/eod';

function stock(symbol: string, composite_score: number): SignalStock {
  return { symbol, composite_score } as unknown as SignalStock;
}

function card(id: string, stocks: SignalStock[], count: number, more: number): SignalCard {
  return {
    id,
    category: 'momentum',
    count,
    more_count: more,
    preview_stocks: stocks,
  } as unknown as SignalCard;
}

const CARDS: SignalCard[] = [
  card('P1', [stock('AAA', 1), stock('BBB', -1), stock('CCC', 0)], 130, 127),
  card('T1', [stock('DDD', 0.5), stock('EEE', -0.25)], 135, 133),
  card('V1', [stock('FFF', 0)], 5, 4),
];

describe('directionOfScore', () => {
  it('부호로만 방향을 정한다 (0·부재 = 중립)', () => {
    expect(directionOfScore(1)).toBe('bull');
    expect(directionOfScore(-0.001)).toBe('bear');
    expect(directionOfScore(0)).toBe('neutral');
    expect(directionOfScore(null)).toBe('neutral');
    expect(directionOfScore(undefined)).toBe('neutral');
  });
});

describe('countDirections', () => {
  it('세그먼트 수치가 그리드에 보일 줄 수와 일치한다', () => {
    const counts = countDirections(CARDS);
    expect(counts).toEqual({ all: 6, bull: 2, bear: 2, neutral: 2 });
    expect(counts.bull + counts.bear + counts.neutral).toBe(counts.all);
  });

  it('세그먼트 수치는 각 방향 필터 결과의 종목 수와 정확히 같다', () => {
    const counts = countDirections(CARDS);
    for (const d of ['bull', 'bear', 'neutral'] as const) {
      const rows = filterCardsByDirection(CARDS, d)
        .reduce((n, c) => n + c.preview_stocks.length, 0);
      expect(rows).toBe(counts[d]);
    }
  });
});

describe('countUniqueSymbols', () => {
  it('중복 종목을 한 번만 센다 — 행 수와 다를 수 있다', () => {
    const dup = [
      card('P1', [stock('AAA', 1), stock('BBB', -1)], 10, 8),
      card('T1', [stock('AAA', 1), stock('CCC', 0)], 10, 8),
    ];
    expect(countDirections(dup).all).toBe(4); // 행 수
    expect(countUniqueSymbols(dup)).toBe(3); // 고유 종목 수
  });

  it('중복이 없으면 행 수와 같다', () => {
    expect(countUniqueSymbols(CARDS)).toBe(6);
    expect(countDirections(CARDS).all).toBe(6);
  });

  it('빈 입력은 0', () => {
    expect(countUniqueSymbols([])).toBe(0);
  });
});

describe('filterCardsByDirection', () => {
  it("'all'은 원본 배열을 그대로 돌려준다", () => {
    expect(filterCardsByDirection(CARDS, 'all')).toBe(CARDS);
  });

  it('방향에 맞는 종목만 남기고 빈 카드는 뺀다', () => {
    const bull = filterCardsByDirection(CARDS, 'bull');
    expect(bull.map((c) => c.id)).toEqual(['P1', 'T1']);
    expect(bull[0].preview_stocks.map((s) => s.symbol)).toEqual(['AAA']);
    expect(bull[1].preview_stocks.map((s) => s.symbol)).toEqual(['DDD']);
  });

  it('필터 후 종목 수가 줄어든다', () => {
    const before = CARDS.reduce((n, c) => n + c.preview_stocks.length, 0);
    const after = filterCardsByDirection(CARDS, 'bull')
      .reduce((n, c) => n + c.preview_stocks.length, 0);
    expect(after).toBeLessThan(before);
  });

  it('카드 총 시그널 수(count)는 모집단 사실이라 보존하고 more_count만 0으로 내린다', () => {
    const bear = filterCardsByDirection(CARDS, 'bear');
    expect(bear[0].count).toBe(130);
    expect(bear[0].more_count).toBe(0);
  });

  it('렌더 key(card.id)가 필터로 바뀌지 않는다 — remount 금지', () => {
    const ids = (d: Parameters<typeof filterCardsByDirection>[1]) =>
      filterCardsByDirection(CARDS, d).map((c) => c.id);
    expect(ids('neutral').every((id) => CARDS.some((c) => c.id === id))).toBe(true);
    expect(ids('bull')).toEqual(['P1', 'T1']);
  });

  it('원본 카드를 변형하지 않는다', () => {
    filterCardsByDirection(CARDS, 'bull');
    expect(CARDS[0].preview_stocks).toHaveLength(3);
    expect(CARDS[0].more_count).toBe(127);
  });
});
