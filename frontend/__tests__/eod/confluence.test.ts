import { describe, it, expect } from 'vitest';
import { buildConfluenceMap, getAxisCount, CONFLUENCE_MIN_AXES } from '@/components/eod/confluence';
import type { SignalCardDetail, SignalStock } from '@/types/eod';

// 최소 stock stub (합류 계산은 symbol만 사용)
function stock(symbol: string): SignalStock {
  return {
    symbol,
    company_name: symbol,
    sector: 'Tech',
    industry: 'x',
    close_price: 1,
    change_percent: 0,
    signal_value: 0,
    signal_label: 'x',
    signal_direction: 'bullish',
    news_context: { headline: '', source: '', url: '', match_type: 'profile', confidence: 'info', age_days: 0 },
    mini_chart_20d: [],
    chain_sight_cta: false,
    composite_score: 0,
    market_cap: 1,
    volume: 1,
    dollar_volume: 1,
  };
}

function card(category: SignalCardDetail['category'], symbols: string[]): Pick<SignalCardDetail, 'category' | 'stocks_by_score'> {
  return { category, stocks_by_score: symbols.map(stock) };
}

describe('buildConfluenceMap — 카테고리 축 단위 합류', () => {
  it('같은 카테고리 여러 카드에 걸쳐도 1축(중복 배제)', () => {
    // P1·P2 둘 다 momentum → AAA는 momentum 1축뿐
    const map = buildConfluenceMap([
      card('momentum', ['AAA']),
      card('momentum', ['AAA']),
    ]);
    expect(map.get('AAA')?.axisCount).toBe(1);
    expect(map.get('AAA')?.categories).toEqual(['momentum']);
  });

  it('서로 다른 카테고리 = 축 누적', () => {
    const map = buildConfluenceMap([
      card('momentum', ['BBB']),
      card('technical', ['BBB']),
      card('volume', ['BBB']),
    ]);
    expect(map.get('BBB')?.axisCount).toBe(3);
    expect(map.get('BBB')?.categories).toEqual(['momentum', 'technical', 'volume']);
  });

  it('categories는 정렬(결정론) + 중복 카테고리와 신규 축 혼합', () => {
    const map = buildConfluenceMap([
      card('volume', ['CCC']),
      card('momentum', ['CCC']),
      card('momentum', ['CCC']), // 중복 momentum
    ]);
    expect(map.get('CCC')?.categories).toEqual(['momentum', 'volume']); // 정렬·중복배제
    expect(map.get('CCC')?.axisCount).toBe(2);
  });

  it('빈 카드/빈 stocks 안전', () => {
    const map = buildConfluenceMap([
      { category: 'momentum', stocks_by_score: [] },
    ]);
    expect(map.size).toBe(0);
  });

  it('getAxisCount: 미로딩 map(undefined)·미존재 심볼 = 0', () => {
    const map = buildConfluenceMap([card('momentum', ['DDD'])]);
    expect(getAxisCount(undefined, 'DDD')).toBe(0);
    expect(getAxisCount(map, 'ZZZ')).toBe(0);
    expect(getAxisCount(map, 'DDD')).toBe(1);
  });

  it('임계 상수 = 2', () => {
    expect(CONFLUENCE_MIN_AXES).toBe(2);
  });
});
