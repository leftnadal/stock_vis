import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StockRow } from '@/components/eod/StockRow';
import type { SignalStock, NewsMatchType } from '@/types/eod';

function mk(overrides: Partial<SignalStock> = {}): SignalStock {
  return {
    symbol: 'NVDA',
    company_name: 'NVIDIA Corp',
    sector: 'Technology',
    industry: 'Semiconductors',
    close_price: 123.45,
    change_percent: 2.5,
    signal_value: 1,
    signal_label: '연속 상승 4일',
    signal_direction: 'bullish',
    news_context: { headline: 'Profile fallback', source: 'profile', url: '', match_type: 'profile', confidence: 'info', age_days: 0 },
    mini_chart_20d: [1, 2, 3, 4],
    chain_sight_cta: false,
    composite_score: 0.7,
    market_cap: 3_000_000_000_000,
    volume: 5_000_000,
    dollar_volume: 800_000_000,
    ...overrides,
  };
}
function news(match_type: NewsMatchType, age = 0): SignalStock['news_context'] {
  return { headline: 'Real headline', source: 's', url: '', match_type, confidence: 'high', age_days: age };
}

describe('StockRow — 기존 정보 보존 회귀 (재배치 허용, 손실 금지)', () => {
  it('심볼·회사명·가격·변화율·시그널라벨·거래량 전부 유지', () => {
    render(<StockRow stock={mk()} />);
    expect(screen.getByText('NVDA')).toBeInTheDocument();
    expect(screen.getByText('NVIDIA Corp')).toBeInTheDocument();
    expect(screen.getByText(/123\.45/)).toBeInTheDocument(); // 가격
    expect(screen.getByText(/2\.50%/)).toBeInTheDocument(); // 변화율
    expect(screen.getByText('연속 상승 4일')).toBeInTheDocument(); // 시그널 라벨
    expect(screen.getByText(/거래량 5\.0M/)).toBeInTheDocument(); // 거래량(보존)
  });

  it('종목 링크 유지(/stocks/NVDA)', () => {
    render(<StockRow stock={mk()} />);
    const link = screen.getByRole('link', { name: 'NVDA' });
    expect(link).toHaveAttribute('href', '/stocks/NVDA');
  });
});

describe('StockRow — 신설 요소 (정칙 ⑸ 체급 결박 + 축 칩)', () => {
  it('시총·거래대금 서브라인 추가(같은 행 블록)', () => {
    render(<StockRow stock={mk()} />);
    expect(screen.getByText(/시총 \$3\.0T/)).toBeInTheDocument();
    expect(screen.getByText(/대금 \$800M/)).toBeInTheDocument();
  });

  it('합류 축≥2 → "N축 합류" 칩 점등', () => {
    render(<StockRow stock={mk()} axisCount={3} />);
    expect(screen.getByText('3축 합류')).toBeInTheDocument();
  });

  it('합류 축<2 → 합류 칩 생략(정칙 ⑴)', () => {
    render(<StockRow stock={mk()} axisCount={1} />);
    expect(screen.queryByText(/축 합류/)).toBeNull();
  });

  it('유효 섹터 칩 렌더 / 결측 섹터는 칩 생략(정칙 ⑴)', () => {
    const { rerender } = render(<StockRow stock={mk({ sector: 'Technology' })} axisCount={2} />);
    expect(screen.getByText('Technology')).toBeInTheDocument();
    rerender(<StockRow stock={mk({ sector: 'Unknown' })} axisCount={0} />);
    expect(screen.queryByText('Unknown')).toBeNull();
  });

  it('실뉴스 칩은 실매칭에서만 / profile 폴백은 생략(정칙 ⑴)', () => {
    const { rerender } = render(<StockRow stock={mk({ news_context: news('symbol_today') })} />);
    expect(screen.getByText('뉴스 · 오늘')).toBeInTheDocument();
    // profile 폴백(기본) → 축 뉴스 칩 없음
    rerender(<StockRow stock={mk()} axisCount={0} />);
    expect(screen.queryByText(/^뉴스 ·/)).toBeNull();
  });

  it('시총 결측(null) → 시총 칩 생략(정칙 ⑴)', () => {
    render(<StockRow stock={mk({ market_cap: null })} />);
    expect(screen.queryByText(/시총 \$/)).toBeNull();
    expect(screen.getByText(/대금 \$800M/)).toBeInTheDocument(); // 대금은 유지
  });
});
