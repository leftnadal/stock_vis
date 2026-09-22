import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { formatCompactUSD } from '@/components/eod/format';
import { StockRow } from '@/components/eod/StockRow';
import type { SignalStock } from '@/types/eod';

describe('format.formatCompactUSD (f 복제 해소 — 행위보존)', () => {
  it('원 구현과 같은 경계·자릿수를 유지한다', () => {
    expect(formatCompactUSD(2_500_000_000_000)).toBe('$2.5T');
    expect(formatCompactUSD(80_000_000_000)).toBe('$80.0B');
    expect(formatCompactUSD(1_000_000_000)).toBe('$1.0B');
    expect(formatCompactUSD(900_000_000)).toBe('$900M');
    expect(formatCompactUSD(999_999)).toBe('$1000K');
    expect(formatCompactUSD(0)).toBeNull();
    expect(formatCompactUSD(-5)).toBeNull();
    expect(formatCompactUSD(null)).toBeNull();
    expect(formatCompactUSD(undefined)).toBeNull();
  });
});

function makeStock(symbol: string): SignalStock {
  return {
    symbol,
    company_name: `${symbol} Inc.`,
    sector: 'Technology',
    close_price: 100,
    change_percent: 1.5,
    signal_label: '테스트 시그널',
    signal_direction: 'bullish',
    composite_score: 1,
    market_cap: 80_000_000_000,
    volume: 1_000_000,
    dollar_volume: 900_000_000,
    mini_chart_20d: [1, 2, 3],
    news_context: null,
    chain_sight_cta: false,
  } as unknown as SignalStock;
}

describe('StockRow memo (⑦-3)', () => {
  it('memo로 감싸도 렌더 결과가 같다(행위보존)', () => {
    render(<StockRow stock={makeStock('AAPL')} axisCount={2} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText(/시총 \$80\.0B/)).toBeInTheDocument();
    expect(screen.getByText(/대금 \$900M/)).toBeInTheDocument();
  });

  it('symbol·axisCount가 같으면 재렌더를 건너뛴다', () => {
    const s = makeStock('MSFT');
    const { rerender } = render(<StockRow stock={s} axisCount={1} />);
    const first = screen.getByText('MSFT');
    rerender(<StockRow stock={{ ...s }} axisCount={1} />);
    // 같은 DOM 노드가 유지되면 memo가 재렌더를 막은 것.
    expect(screen.getByText('MSFT')).toBe(first);
  });

  it('axisCount가 바뀌면 재렌더된다', () => {
    const s = makeStock('NVDA');
    const { rerender } = render(<StockRow stock={s} axisCount={0} />);
    expect(screen.queryByText(/축 합류/)).not.toBeInTheDocument();
    rerender(<StockRow stock={s} axisCount={3} />);
    expect(screen.getByText(/3축 합류/)).toBeInTheDocument();
  });
});
