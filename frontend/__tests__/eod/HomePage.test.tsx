import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { EODDashboardData } from '@/types/eod';
import type { QuadrantSector } from '@/types/quadrant';

// ── 의존 모킹(페이지 배선만 검증 — 하위 컴포넌트 자체 로직은 각 테스트 소관) ──
const params = vi.hoisted(() => ({ value: new URLSearchParams() }));
vi.mock('next/navigation', () => ({
  useSearchParams: () => params.value,
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => '/',
}));

const dashboard = vi.hoisted(() => ({ data: undefined as unknown }));
vi.mock('@/hooks/useEODDashboard', () => ({
  useEODDashboard: () => ({ data: dashboard.data, isLoading: false, error: null }),
  useSignalDetail: () => ({ data: undefined, isLoading: false }),
}));

const quadrant = vi.hoisted(() => ({ data: undefined as unknown }));
vi.mock('@/hooks/useSectorQuadrant', () => ({ useSectorQuadrant: () => ({ data: quadrant.data }) }));

vi.mock('@/components/eod/useConfluenceMap', () => ({
  useConfluenceMap: () => ({ map: new Map(), stockIndex: new Map(), isLoading: false }),
}));

vi.mock('@/components/charts/SectorQuadrant', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/components/charts/SectorQuadrant')>()),
  SectorQuadrant: () => <div data-testid="sector-quadrant" />,
}));
vi.mock('@/components/strip/NewsStrip', () => ({ NewsStrip: () => null }));
vi.mock('@/components/strip/MacroStrip', () => ({ MacroStrip: () => null }));
vi.mock('@/components/strip/EventStrip', () => ({ EventStrip: () => null }));
vi.mock('@/components/dashboard/CoverageStrip', () => ({ CoverageStrip: () => null }));
vi.mock('@/hooks/useImpressionTracker', () => ({ useImpressionTracker: () => ({ ref: { current: null }, onClick: () => {} }) }));

import Home from '@/app/page';

function sector(name: string, heat: number | null, breadth: number | null): QuadrantSector {
  return { sector: name, heat, breadth_curr: breadth } as unknown as QuadrantSector;
}

const DATA = {
  generated_at: '2026-09-16T22:30:40Z',
  trading_date: '2026-09-16',
  is_stale: false,
  market_summary: {
    sp500_change: 0, qqq_change: 0, vix: 15, vix_regime: 'normal', total_signals: 0,
    bullish_count: 0, bearish_count: 0, stocks_with_signals: 0, stock_universe: 0, headline: '',
  },
  signal_cards: [],
  pipeline_meta: {} as EODDashboardData['pipeline_meta'],
  recommendations: [
    {
      rank: 1, ticker: 'ABBV', company_name: 'AbbVie', signal_tag: 'P1', confidence: 'high', conf_ver: 1,
      composite_score: 1, thesis: '논리',
      perspectives: { technical: '기술 서술', fundamental: null, news_context: null }, risk: null,
    },
  ],
} as unknown as EODDashboardData;

beforeEach(() => {
  dashboard.data = DATA;
  quadrant.data = undefined;
  params.value = new URLSearchParams();
});

describe('Home — 추천 드로어 진입', () => {
  it('카드 본문 클릭 → 우측 드로어(RecommendationDetailSheet)가 열리고 ESC로 닫힌다', () => {
    render(<Home />);
    expect(screen.queryByRole('heading', { name: '세 관점' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /추천 ABBV/ }));
    expect(screen.getByRole('heading', { name: '세 관점' })).toBeInTheDocument();
    expect(screen.getByText('기술 서술', { selector: 'dd' })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('heading', { name: '세 관점' })).toBeNull();
  });
});
