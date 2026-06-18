/**
 * Slice 3 — 타입·데이터 연결 검증
 *
 * is_fallback·volume_z·volatility_pct가
 * EventRankingItem 타입 → EventRanking → LowLiquidityPanel/펼침까지
 * 올바른 키로 흐르는지 확인한다.
 *
 * 신규 백엔드 없음 — 합성 픽스처 기반.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EventRanking from '@/components/chainsight/EventRanking';
import type { EventRankingItem } from '@/types/chainsight';

vi.mock('@/services/chainsightService', () => ({
  fetchEventStocks: vi.fn(),
}));
vi.mock('next/navigation', () => ({
  useRouter: () => ({ back: vi.fn(), push: vi.fn() }),
}));
vi.mock('next/link', () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));
vi.mock('@/constants/eventThemes', () => ({
  getLabelForTheme: () => ({ ko: '반도체', icon: 'Tag' }),
  METRIC_INFO: {
    trend_quality: { field: 'trend_quality', label: '추세강도', tier: 'primary', description: '', example: '', range: '' },
    theme_beta: { field: 'theme_beta', label: '그룹 민감도', tier: 'primary', description: '', example: '', range: '' },
    capture_spread: { field: 'capture_spread', label: '주도우위', tier: 'primary', description: '', example: '', range: '' },
    theme_alpha: { field: 'theme_alpha', label: '그룹 초과수익', tier: 'supplementary', description: '', example: '', range: '' },
    up_capture: { field: 'up_capture', label: '상승 포착', tier: 'supplementary', description: '', example: '', range: '' },
    down_capture: { field: 'down_capture', label: '하락 방어', tier: 'supplementary', description: '', example: '', range: '' },
    volume_z: { field: 'volume_z', label: '거래량 z', tier: 'context', description: '', example: '', range: '' },
    volatility_pct: { field: 'volatility_pct', label: '변동성', tier: 'context', description: '', example: '', range: '' },
  },
}));
vi.mock('@/components/chainsight/MetricInfoPopover', () => ({
  default: ({ metricKey }: { metricKey: string }) => (
    <button data-testid={`metric-popover-${metricKey}`} aria-label={`${metricKey} 설명`} />
  ),
}));
vi.mock('lucide-react', () => ({
  ArrowLeft: () => <span data-testid="arrow-left" />,
  ChevronDown: () => <span data-testid="chevron-down" />,
  ChevronUp: () => <span data-testid="chevron-up" />,
  AlertTriangle: () => <span data-testid="alert-triangle" />,
}));

import { fetchEventStocks } from '@/services/chainsightService';

// ── 합성 픽스처 ───────────────────────────────────────────────────────────

/** volume_z·volatility_pct 값이 있는 정상 종목 */
const stockWithContext: EventRankingItem = {
  symbol: 'AAPL',
  name: 'Apple Inc.',
  score: 80.0,
  raw_return: 0.05,
  volume_z: 2.35,
  volatility_pct: 0.67,
  is_low_liquidity: false,
  is_fallback: false,
  trend_quality: 0.70,
  theme_alpha: 0.03,
  theme_beta: 1.10,
  up_capture: 1.05,
  down_capture: 0.95,
  capture_spread: 10,
};

/** is_fallback=true 합성 픽스처 (현재 prod 0종목 → 이 테스트가 유일한 가드) */
const fallbackStock: EventRankingItem = {
  symbol: 'XYZW',
  name: 'Fallback Corp',
  score: 30.0,
  raw_return: -0.01,
  volume_z: 0.5,
  volatility_pct: 0.3,
  is_low_liquidity: false,
  is_fallback: true,
  trend_quality: null,
  theme_alpha: null,
  theme_beta: null,
  up_capture: null,
  down_capture: null,
  capture_spread: null,
};

/** is_low_liquidity=true AND is_fallback=true (두 경고 공존) */
const bothFlagsStock: EventRankingItem = {
  symbol: 'LOWQ',
  name: 'Low Quality Inc.',
  score: 20.0,
  raw_return: 0.001,
  volume_z: 0.1,
  volatility_pct: 0.85,
  is_low_liquidity: true,
  is_fallback: true,
  trend_quality: null,
  theme_alpha: null,
  theme_beta: null,
  up_capture: null,
  down_capture: null,
  capture_spread: null,
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// ── 테스트 ────────────────────────────────────────────────────────────────

describe('Slice 3 — 필드 매핑 연결 검증', () => {
  it('volume_z가 EventRankingItem에서 펼침 영역까지 올바르게 전달된다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([stockWithContext]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('AAPL');
    fireEvent.click(screen.getByRole('button', { name: 'AAPL 상세 펼치기' }));
    // volume_z=2.35 → toFixed(2) = '2.35'
    expect(screen.getByText('2.35')).toBeInTheDocument();
  });

  it('volatility_pct가 EventRankingItem에서 펼침 영역까지 올바르게 전달된다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([stockWithContext]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('AAPL');
    fireEvent.click(screen.getByRole('button', { name: 'AAPL 상세 펼치기' }));
    // volatility_pct=0.67 → (0.67*100).toFixed(0) = '67%'
    expect(screen.getByText('67%')).toBeInTheDocument();
  });

  it('is_fallback=true가 LowLiquidityPanel까지 전달되어 경고를 렌더한다 (R4 가드)', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([fallbackStock]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('XYZW');
    // is_fallback=true → 경고 영역 렌더
    expect(screen.getByText(/데이터가 부족해 보정된 값이에요/)).toBeInTheDocument();
  });

  it('is_low_liquidity AND is_fallback 둘 다 LowLiquidityPanel까지 전달된다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([bothFlagsStock]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('LOWQ');
    expect(screen.getByText(/거래량이 얕아 체결·청산이 불리할 수 있습니다/)).toBeInTheDocument();
    expect(screen.getByText(/데이터가 부족해 보정된 값이에요/)).toBeInTheDocument();
  });

  it('is_fallback=false인 종목에 경고 영역이 없다 (is_low_liquidity도 false)', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([stockWithContext]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('AAPL');
    expect(screen.queryByText(/거래량이 얕아/)).not.toBeInTheDocument();
    expect(screen.queryByText(/보정된 값/)).not.toBeInTheDocument();
  });

  it('MetricKey volume_z·volatility_pct로 MetricInfoPopover가 호출된다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([stockWithContext]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('AAPL');
    fireEvent.click(screen.getByRole('button', { name: 'AAPL 상세 펼치기' }));
    expect(screen.getByTestId('metric-popover-volume_z')).toBeInTheDocument();
    expect(screen.getByTestId('metric-popover-volatility_pct')).toBeInTheDocument();
  });
});
