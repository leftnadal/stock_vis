import { describe, it, expect } from 'vitest';
import {
  applyScannerFilters,
  sortScannerStocks,
  hasRealNews,
  validSector,
  newsRecencyLabel,
  availableSectors,
  DEFAULT_SCANNER_FILTERS,
  type ScannerFilters,
} from '@/components/eod/scannerFilters';
import { buildConfluenceMap } from '@/components/eod/confluence';
import type { SignalStock, NewsMatchType, SignalCardDetail } from '@/types/eod';

function mk(overrides: Partial<SignalStock>): SignalStock {
  return {
    symbol: 'X',
    company_name: 'X',
    sector: 'Tech',
    industry: 'x',
    close_price: 1,
    change_percent: 0,
    signal_value: 0,
    signal_label: 'x',
    signal_direction: 'bullish',
    news_context: { headline: 'h', source: '', url: '', match_type: 'profile', confidence: 'info', age_days: 0 },
    mini_chart_20d: [],
    chain_sight_cta: false,
    composite_score: 0,
    market_cap: 1_000_000_000,
    volume: 1000,
    dollar_volume: 1_000_000,
    ...overrides,
  };
}
function news(match_type: NewsMatchType, age = 0): SignalStock['news_context'] {
  return { headline: 'real', source: 's', url: '', match_type, confidence: 'high', age_days: age };
}

const f = (o: Partial<ScannerFilters>): ScannerFilters => ({ ...DEFAULT_SCANNER_FILTERS, ...o });

describe('validSector / hasRealNews / newsRecencyLabel', () => {
  it('validSector: 결측·Unknown·N/A = false', () => {
    expect(validSector('Tech')).toBe(true);
    expect(validSector('')).toBe(false);
    expect(validSector('Unknown')).toBe(false);
    expect(validSector(null)).toBe(false);
  });
  it('hasRealNews: profile 폴백/빈 headline = false, 실매칭 = true', () => {
    expect(hasRealNews(mk({}))).toBe(false); // 기본 profile
    expect(hasRealNews(mk({ news_context: news('symbol_today') }))).toBe(true);
    expect(hasRealNews(mk({ news_context: news('industry_7d', 3) }))).toBe(true);
    expect(hasRealNews(mk({ news_context: { ...news('symbol_7d'), headline: '' } }))).toBe(false);
  });
  it('newsRecencyLabel: 상태 서술(감성 아님)', () => {
    expect(newsRecencyLabel(mk({ news_context: news('symbol_today') }))).toBe('뉴스 · 오늘');
    expect(newsRecencyLabel(mk({ news_context: news('symbol_7d', 3) }))).toBe('뉴스 · 3일 전');
    expect(newsRecencyLabel(mk({ news_context: news('industry_7d', 2) }))).toBe('업종 뉴스');
  });
});

describe('applyScannerFilters — 각 조건 + 조합', () => {
  const map = buildConfluenceMap([
    { category: 'momentum', stocks_by_score: [mk({ symbol: 'A' }), mk({ symbol: 'B' })] },
    { category: 'technical', stocks_by_score: [mk({ symbol: 'A' })] }, // A = 2축
  ] as Pick<SignalCardDetail, 'category' | 'stocks_by_score'>[]);

  const stocks = [
    mk({ symbol: 'A', sector: 'Tech', market_cap: 5e9, dollar_volume: 5e6, news_context: news('symbol_today') }),
    mk({ symbol: 'B', sector: 'Energy', market_cap: 1e9, dollar_volume: 1e6 }), // profile 뉴스
  ];

  it('무필터 = 전체 통과', () => {
    expect(applyScannerFilters(stocks, DEFAULT_SCANNER_FILTERS, map)).toHaveLength(2);
  });
  it('섹터', () => {
    expect(applyScannerFilters(stocks, f({ sector: 'Energy' }), map).map((s) => s.symbol)).toEqual(['B']);
  });
  it('시총 하한', () => {
    expect(applyScannerFilters(stocks, f({ marketCapMin: 2e9 }), map).map((s) => s.symbol)).toEqual(['A']);
  });
  it('거래대금 하한', () => {
    expect(applyScannerFilters(stocks, f({ dollarVolumeMin: 3e6 }), map).map((s) => s.symbol)).toEqual(['A']);
  });
  it('합류 N축 이상', () => {
    expect(applyScannerFilters(stocks, f({ minAxes: 2 }), map).map((s) => s.symbol)).toEqual(['A']);
  });
  it('뉴스 유무(실매칭만)', () => {
    expect(applyScannerFilters(stocks, f({ newsOnly: true }), map).map((s) => s.symbol)).toEqual(['A']);
  });
  it('조합(섹터+시총+합류)', () => {
    expect(applyScannerFilters(stocks, f({ sector: 'Tech', marketCapMin: 2e9, minAxes: 2 }), map).map((s) => s.symbol)).toEqual(['A']);
    expect(applyScannerFilters(stocks, f({ sector: 'Energy', minAxes: 2 }), map)).toHaveLength(0);
  });
  it('map 미로딩(undefined) 시 minAxes 필터는 전건 탈락(0축)', () => {
    expect(applyScannerFilters(stocks, f({ minAxes: 2 }), undefined)).toHaveLength(0);
  });
});

describe('availableSectors', () => {
  it('유효 섹터만·정렬·중복배제', () => {
    const stocks = [mk({ sector: 'Tech' }), mk({ sector: 'Energy' }), mk({ sector: 'Tech' }), mk({ sector: 'Unknown' })];
    expect(availableSectors(stocks)).toEqual(['Energy', 'Tech']);
  });
});

describe('sortScannerStocks', () => {
  const map = buildConfluenceMap([
    { category: 'momentum', stocks_by_score: [mk({ symbol: 'A' }), mk({ symbol: 'B' }), mk({ symbol: 'C' })] },
    { category: 'technical', stocks_by_score: [mk({ symbol: 'A' }), mk({ symbol: 'B' })] },
    { category: 'volume', stocks_by_score: [mk({ symbol: 'A' })] }, // A=3축 B=2축 C=1축
  ] as Pick<SignalCardDetail, 'category' | 'stocks_by_score'>[]);
  const stocks = [mk({ symbol: 'C', composite_score: 0.9 }), mk({ symbol: 'A', composite_score: 0.1 }), mk({ symbol: 'B', composite_score: 0.5 })];

  it('합류순 = 축 수 desc, 동률 composite desc', () => {
    expect(sortScannerStocks(stocks, 'confluence', map, { volume: [], return: [], market_cap: [] }).map((s) => s.symbol)).toEqual(['A', 'B', 'C']);
  });
  it('기존 rank 리스트 순서 유지(volume)', () => {
    expect(sortScannerStocks(stocks, 'volume', map, { volume: ['B', 'C', 'A'], return: [], market_cap: [] }).map((s) => s.symbol)).toEqual(['B', 'C', 'A']);
  });
  it('rank 리스트 비면 원본 유지', () => {
    expect(sortScannerStocks(stocks, 'volume', map, { volume: [], return: [], market_cap: [] }).map((s) => s.symbol)).toEqual(['C', 'A', 'B']);
  });
});
