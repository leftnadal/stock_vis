import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SignalDetailSheet } from '@/components/eod/SignalDetailSheet';
import { buildConfluenceMap } from '@/components/eod/confluence';
import type { SignalCard, SignalCardDetail, SignalStock } from '@/types/eod';

function stock(symbol: string, over: Partial<SignalStock> = {}): SignalStock {
  return {
    symbol,
    company_name: `${symbol} Inc`,
    sector: 'Technology',
    industry: 'x',
    close_price: 100,
    change_percent: 1,
    signal_value: 1,
    signal_label: 'label',
    signal_direction: 'bullish',
    news_context: { headline: 'p', source: 'profile', url: '', match_type: 'profile', confidence: 'info', age_days: 0 },
    mini_chart_20d: [1, 2],
    chain_sight_cta: false,
    composite_score: 0.5,
    market_cap: 2_000_000_000,
    volume: 1000,
    dollar_volume: 2_000_000,
    ...over,
  };
}

const detail: SignalCardDetail = {
  signal_id: 'P1',
  category: 'momentum',
  title: '연속 상승',
  total_count: 2,
  stocks_by_score: [stock('AAA'), stock('BBB')],
  stocks_by_volume: [stock('AAA'), stock('BBB')],
  stocks_by_return: [stock('AAA'), stock('BBB')],
  stocks_by_market_cap: [stock('AAA'), stock('BBB')],
  sector_distribution: ['Technology'],
};

vi.mock('@/hooks/useEODDashboard', () => ({
  useSignalDetail: () => ({ data: detail, isLoading: false }),
}));

const card: SignalCard = {
  id: 'P1',
  category: 'momentum',
  color: '#000',
  title: '연속 상승',
  count: 2,
  description_ko: '',
  education_tip: '',
  education_risk: '',
  preview_stocks: [stock('AAA'), stock('BBB')],
  more_count: 0,
  chain_sight_sectors: [],
  rank_by_volume: ['AAA', 'BBB'],
  rank_by_return: ['AAA', 'BBB'],
  rank_by_market_cap: ['AAA', 'BBB'],
};

describe('SignalDetailSheet — 패널 확장(STEP 5)', () => {
  it('정직성 한 줄 고정 렌더', () => {
    render(<SignalDetailSheet card={card} onClose={() => {}} />);
    expect(
      screen.getByText('신호는 주목 후보를 고르는 렌즈이며 수익을 보장하지 않습니다.'),
    ).toBeInTheDocument();
  });

  it('미커버 축 명시(가치평가·퀄리티·관계) — 정칙 ⑴ 정보판', () => {
    render(<SignalDetailSheet card={card} onClose={() => {}} />);
    expect(screen.getByText(/미커버\(곧\): 가치평가 · 퀄리티 · 관계/)).toBeInTheDocument();
  });

  it('필터 바 렌더 + 결과/총 종목 수 표기', () => {
    render(<SignalDetailSheet card={card} onClose={() => {}} />);
    expect(screen.getByRole('group', { name: '스캐너 필터' })).toBeInTheDocument();
    expect(screen.getByText('2/2종목')).toBeInTheDocument();
  });

  it('합류 지도 주입 시 축 칩 렌더(AAA=2축)', () => {
    const map = buildConfluenceMap([
      { category: 'momentum', stocks_by_score: [stock('AAA')] },
      { category: 'technical', stocks_by_score: [stock('AAA')] },
    ]);
    render(<SignalDetailSheet card={card} onClose={() => {}} confluenceMap={map} />);
    expect(screen.getByText('2축 합류')).toBeInTheDocument();
  });
});
