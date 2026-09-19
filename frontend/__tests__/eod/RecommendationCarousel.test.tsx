import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RecommendationCarousel } from '@/components/eod/RecommendationCarousel';
import { buildConfluenceMap, buildStockIndex } from '@/components/eod/confluence';
import type { Recommendation, SignalStock } from '@/types/eod';

function stock(symbol: string, dollar_volume: number): SignalStock {
  return { symbol, dollar_volume } as unknown as SignalStock;
}

function rec(overrides: Partial<Recommendation>): Recommendation {
  return {
    rank: 1,
    ticker: 'AAA',
    company_name: 'Alpha Inc.',
    signal_tag: 'V1',
    confidence: 'high',
    conf_ver: 1,
    composite_score: 0.5,
    thesis: null,
    perspectives: { technical: null, fundamental: null, news_context: null },
    risk: null,
    ...overrides,
  };
}

describe('RecommendationCarousel', () => {
  it('하위호환: recommendations 부재 시 아무것도 렌더하지 않는다', () => {
    const { container } = render(<RecommendationCarousel recommendations={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it('하위호환: 빈 배열이면 표면 생략', () => {
    const { container } = render(<RecommendationCarousel recommendations={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('R3 정렬: 축 수 내림 → 거래대금 내림 → ticker 오름 (composite_score 무시)', () => {
    const map = buildConfluenceMap([
      { category: 'momentum', stocks_by_score: [stock('THREE', 1), stock('TWO_LOWDV', 1), stock('TWO_HIGHDV', 900)] },
      { category: 'volume', stocks_by_score: [stock('THREE', 1), stock('TWO_LOWDV', 1), stock('TWO_HIGHDV', 900)] },
      { category: 'technical', stocks_by_score: [stock('THREE', 1)] },
    ]);
    const index = buildStockIndex([
      { category: 'momentum', stocks_by_score: [stock('THREE', 1), stock('TWO_LOWDV', 10), stock('TWO_HIGHDV', 900), stock('ZERO_B', 50), stock('ZERO_A', 50)] },
    ]);
    render(
      <RecommendationCarousel
        confluenceMap={map}
        stockIndex={index}
        recommendations={[
          rec({ ticker: 'ZERO_B', composite_score: 1 }),
          rec({ ticker: 'TWO_LOWDV', composite_score: 1 }),
          rec({ ticker: 'NOJOIN', composite_score: -1 }),
          rec({ ticker: 'ZERO_A', composite_score: 0.1 }),
          rec({ ticker: 'TWO_HIGHDV', composite_score: -1 }),
          rec({ ticker: 'THREE', composite_score: 0.2 }),
        ]}
      />,
    );
    const order = screen.getAllByRole('listitem').map((el) => el.querySelector('.text-lg')?.textContent);
    // 0축 셋: 대금 50=50 → ticker 오름(ZERO_A < ZERO_B), 조인 실패(NOJOIN) = 맨 뒤
    expect(order).toEqual(['THREE', 'TWO_HIGHDV', 'TWO_LOWDV', 'ZERO_A', 'ZERO_B', 'NOJOIN']);
  });

  it('합류 지도 로딩 중에는 캐러셀만 스켈레톤(카드 미렌더 — 도착 시 재정렬 튐 방지)', () => {
    render(<RecommendationCarousel confluenceLoading recommendations={[rec({ ticker: 'AAA' })]} />);
    expect(screen.getByTestId('recommendation-skeleton')).toBeInTheDocument();
    expect(screen.queryByText('AAA')).toBeNull();
    expect(screen.getByText('오늘의 추천')).toBeInTheDocument();
  });

  it('로딩이 끝났는데 지도가 없으면(요청 실패) 축 0으로 렌더(정칙 ⑴)', () => {
    render(<RecommendationCarousel confluenceLoading={false} recommendations={[rec({ ticker: 'AAA' })]} />);
    expect(screen.queryByTestId('recommendation-skeleton')).toBeNull();
    expect(screen.getByText('AAA')).toBeInTheDocument();
  });

  it('카드 본문 클릭 → onSelect(rec)', () => {
    const onSelect = vi.fn();
    render(<RecommendationCarousel onSelect={onSelect} recommendations={[rec({ ticker: 'AAA' })]} />);
    fireEvent.click(screen.getByRole('button', { name: /추천 AAA/ }));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ ticker: 'AAA' }));
  });

  it('방향을 동사 라벨로 이중표기(색 단독 인코딩 금지)', () => {
    render(
      <RecommendationCarousel
        recommendations={[
          rec({ ticker: 'BUY', composite_score: 0.8 }),
          rec({ ticker: 'SELL', composite_score: -0.8 }),
        ]}
      />,
    );
    expect(screen.getByText('매수')).toBeTruthy();
    expect(screen.getByText('매도·회피')).toBeTruthy();
  });

  it('placeholder 3키 null → ghost 스트립 렌더', () => {
    render(<RecommendationCarousel recommendations={[rec({})]} />);
    expect(screen.getByText(/곧: 논리/)).toBeTruthy();
  });

  it('thesis 채워지면(additive-within) 실내용 승격, ghost 미표시', () => {
    render(
      <RecommendationCarousel
        recommendations={[rec({ thesis: '실제 논리 텍스트' })]}
      />,
    );
    expect(screen.getByText('실제 논리 텍스트')).toBeTruthy();
    expect(screen.queryByText(/곧: 논리/)).toBeNull();
  });

  it('카드가 체인사이트로 진입 링크를 가진다', () => {
    render(<RecommendationCarousel recommendations={[rec({ ticker: 'NVDA' })]} />);
    const link = screen.getByRole('link', { name: /체인사이트/ });
    expect(link.getAttribute('href')).toBe('/stocks/NVDA?tab=chain-sight');
  });
});
