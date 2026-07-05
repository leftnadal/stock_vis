import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RecommendationCarousel } from '@/components/eod/RecommendationCarousel';
import type { Recommendation } from '@/types/eod';

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

  it('|composite_score| 내림차순으로 방어 정렬(부호 무관 강도순)', () => {
    render(
      <RecommendationCarousel
        recommendations={[
          rec({ ticker: 'WEAK', composite_score: 0.2 }),
          rec({ ticker: 'SELL', composite_score: -0.9 }),
          rec({ ticker: 'MID', composite_score: 0.6 }),
        ]}
      />,
    );
    const items = screen.getAllByRole('listitem');
    const order = items.map((el) => el.textContent);
    expect(order[0]).toContain('SELL'); // |0.9|
    expect(order[1]).toContain('MID'); // |0.6|
    expect(order[2]).toContain('WEAK'); // |0.2|
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
