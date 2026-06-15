import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EventRanking from '@/components/chainsight/EventRanking';

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
  getLabelForTheme: (theme: string) => ({
    ko: theme === 'semiconductor' ? '반도체' : theme,
    icon: 'Tag',
  }),
}));

vi.mock('lucide-react', () => ({
  ArrowLeft: () => <span data-testid="arrow-left" />,
  ChevronDown: () => <span data-testid="chevron-down" />,
  ChevronUp: () => <span data-testid="chevron-up" />,
  AlertTriangle: () => <span data-testid="alert-triangle" />,
}));

import { fetchEventStocks } from '@/services/chainsightService';

const mockStocks = [
  {
    symbol: 'NVDA',
    name: 'NVIDIA Corporation',
    score: 92.5,
    raw_return: 0.08,
    volume_z: 3.2,
    volatility_pct: 0.45,
    is_low_liquidity: false,
  },
  {
    symbol: 'SMCI',
    name: 'Super Micro Computer',
    score: 41.0,
    raw_return: 0.02,
    volume_z: 0.8,
    volatility_pct: 0.72,
    is_low_liquidity: true,
  },
  {
    symbol: 'AMD',
    name: 'Advanced Micro Devices',
    score: 75.0,
    raw_return: -0.03,
    volume_z: 1.5,
    volatility_pct: 0.30,
    is_low_liquidity: false,
  },
];

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('EventRanking', () => {
  beforeEach(() => vi.clearAllMocks());

  it('로딩 상태를 표시한다', () => {
    vi.mocked(fetchEventStocks).mockReturnValue(new Promise(() => {}));
    render(<EventRanking theme="semiconductor" />, { wrapper });
    expect(screen.getByText('로딩 중...')).toBeInTheDocument();
  });

  it('헤더에 한글 라벨과 "관련 종목 그룹"을 표시한다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue(mockStocks);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    expect(await screen.findByText('반도체 — 관련 종목 그룹')).toBeInTheDocument();
  });

  it('score 내림차순으로 종목을 정렬한다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue(mockStocks);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    const rows = screen.getAllByText(/NVDA|AMD|SMCI/);
    // First should be NVDA(92.5), then AMD(75.0), then SMCI(41.0)
    const symbols = screen.getAllByText(/^(NVDA|AMD|SMCI)$/);
    expect(symbols[0].textContent).toBe('NVDA');
    expect(symbols[1].textContent).toBe('AMD');
    expect(symbols[2].textContent).toBe('SMCI');
  });

  it('is_low_liquidity=true인 종목에 "저유동성" 배지를 표시한다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue(mockStocks);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('SMCI');
    expect(screen.getByText('저유동성')).toBeInTheDocument();
  });

  it('is_low_liquidity=false인 종목에는 배지가 없다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[0]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    expect(screen.queryByText('저유동성')).not.toBeInTheDocument();
  });

  it('빈 데이터면 빈 상태 메시지를 표시한다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    expect(await screen.findByText('종목 데이터가 없습니다')).toBeInTheDocument();
  });

  it('음수 수익률은 ▼로 표시된다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[2]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('AMD');
    expect(screen.getByText(/▼/)).toBeInTheDocument();
  });

  it('fetchEventStocks를 theme 파라미터로 호출한다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([]);
    render(<EventRanking theme="robotics_ai" />, { wrapper });
    await screen.findByText('종목 데이터가 없습니다');
    expect(fetchEventStocks).toHaveBeenCalledWith('robotics_ai');
  });

  it('랭킹 행을 클릭하면 /chainsight/<symbol> 으로 이동하는 링크를 렌더한다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[0]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    const link = screen.getByRole('link', { name: /NVDA/ });
    expect(link).toHaveAttribute('href', '/chainsight/NVDA');
  });
});
