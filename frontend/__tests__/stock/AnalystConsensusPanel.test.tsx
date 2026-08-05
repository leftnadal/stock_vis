/**
 * SFI-I-2 Part 2 — AnalystConsensusPanel 테스트.
 * 순수 헬퍼(업사이드·추세 변환) + View 렌더(present/null) + 컨테이너 fetch.
 */
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import AnalystConsensusPanel, {
  AnalystConsensusPanelView,
  computeUpsidePct,
  toTrendSeries,
} from '@/components/stock/AnalystConsensusPanel';
import { AnalystSignalData, stockService } from '@/services/stock';

const FULL: AnalystSignalData = {
  available: true,
  symbol: 'AAPL',
  captured_at: '2026-08-04T22:30:00Z',
  source: 'fmp',
  target: { consensus: '341.11', high: '400', low: '245', median: '350' },
  grades: { strong_buy: 1, buy: 70, hold: 32, sell: 8, strong_sell: 0, consensus: 'Buy' },
  grades_historical: [
    { date: '2026-08-01', analystRatingsStrongBuy: 6, analystRatingsBuy: 22, analystRatingsHold: 14, analystRatingsSell: 2, analystRatingsStrongSell: 2 },
    { date: '2026-07-01', analystRatingsStrongBuy: 5, analystRatingsBuy: 20, analystRatingsHold: 16, analystRatingsSell: 3, analystRatingsStrongSell: 2 },
  ],
  rating: 'B',
  overall_score: 3,
};

describe('computeUpsidePct', () => {
  it('양수 업사이드', () => {
    expect(computeUpsidePct('110', 100)).toBeCloseTo(10);
  });
  it('음수 업사이드', () => {
    expect(computeUpsidePct('90', 100)).toBeCloseTo(-10);
  });
  it('현재가 0/null 또는 목표가 null → null', () => {
    expect(computeUpsidePct('110', 0)).toBeNull();
    expect(computeUpsidePct('110', null)).toBeNull();
    expect(computeUpsidePct(null, 100)).toBeNull();
  });
});

describe('toTrendSeries', () => {
  it('최신순→오래된순 변환 + 매수계열 비중%', () => {
    const t = toTrendSeries(FULL.grades_historical);
    expect(t).toHaveLength(2);
    expect(t[0].date).toBe('2026-07-01'); // reverse → 오래된 먼저(차트 좌)
    // 07-01: (5+20)/(5+20+16+3+2)=25/46 ≈ 54%
    expect(t[0].buyRatio).toBe(54);
  });
  it('빈 입력 → []', () => {
    expect(toTrendSeries(undefined)).toEqual([]);
    expect(toTrendSeries([])).toEqual([]);
  });
});

describe('AnalystConsensusPanelView', () => {
  it('데이터 있음 → 목표가·업사이드·분포·추세 렌더', () => {
    render(<AnalystConsensusPanelView data={FULL} currentPrice={300} />);
    expect(screen.getByTestId('analyst-panel')).toBeInTheDocument();
    expect(screen.getByText(/\$341\.11/)).toBeInTheDocument();
    // upside = (341.11-300)/300*100 ≈ 13.7%
    expect(screen.getByTestId('analyst-upside')).toHaveTextContent('13.7%');
    expect(screen.getByTestId('analyst-distribution')).toBeInTheDocument();
    expect(screen.getByTestId('analyst-trend')).toBeInTheDocument();
  });
  it('available:false → 미설정 폴백(유령 미노출)', () => {
    render(<AnalystConsensusPanelView data={{ available: false, symbol: 'NOPE' }} currentPrice={100} />);
    expect(screen.getByTestId('analyst-panel-empty')).toHaveTextContent('미설정');
    expect(screen.queryByTestId('analyst-panel')).not.toBeInTheDocument();
  });
});

describe('AnalystConsensusPanel (컨테이너 fetch)', () => {
  it('fetch 성공 → 패널 렌더', async () => {
    vi.spyOn(stockService, 'getAnalystSignals').mockResolvedValue(FULL);
    render(<AnalystConsensusPanel symbol="AAPL" currentPrice={300} />);
    await waitFor(() => expect(screen.getByTestId('analyst-panel')).toBeInTheDocument());
    expect(screen.getByText('애널리스트 컨센서스')).toBeInTheDocument();
  });
  it('미수집(available:false) → 미설정 폴백', async () => {
    vi.spyOn(stockService, 'getAnalystSignals').mockResolvedValue({ available: false, symbol: 'X' });
    render(<AnalystConsensusPanel symbol="X" currentPrice={100} />);
    await waitFor(() => expect(screen.getByTestId('analyst-panel-empty')).toBeInTheDocument());
  });
});
