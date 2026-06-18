import { render, screen, fireEvent, waitFor } from '@testing-library/react';
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
  METRIC_INFO: {
    trend_quality: { field: 'trend_quality', label: '추세강도', tier: 'primary', description: '', example: '', range: '' },
    theme_beta: { field: 'theme_beta', label: '그룹 민감도', tier: 'primary', description: '', example: '', range: '' },
    capture_spread: { field: 'capture_spread', label: '주도우위', tier: 'primary', description: '', example: '', range: '' },
    theme_alpha: { field: 'theme_alpha', label: '그룹 초과수익', tier: 'supplementary', description: '', example: '', range: '' },
    up_capture: { field: 'up_capture', label: '상승 포착', tier: 'supplementary', description: '', example: '', range: '' },
    down_capture: { field: 'down_capture', label: '하락 방어', tier: 'supplementary', description: '', example: '', range: '' },
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
import type { EventRankingItem } from '@/types/chainsight';

const mockStocks: EventRankingItem[] = [
  {
    symbol: 'NVDA',
    name: 'NVIDIA Corporation',
    score: 92.5,
    raw_return: 0.08,
    volume_z: 3.2,
    volatility_pct: 0.45,
    is_low_liquidity: false,
    trend_quality: 0.81,
    theme_alpha: 0.05,
    theme_beta: 1.34,
    up_capture: 1.18,
    down_capture: 0.99,
    capture_spread: 19,
    is_fallback: false,
  },
  {
    symbol: 'SMCI',
    name: 'Super Micro Computer',
    score: 41.0,
    raw_return: 0.02,
    volume_z: 0.8,
    volatility_pct: 0.72,
    is_low_liquidity: true,
    trend_quality: null,
    theme_alpha: null,
    theme_beta: null,
    up_capture: null,
    down_capture: null,
    capture_spread: null,
    is_fallback: false,
  },
  {
    symbol: 'AMD',
    name: 'Advanced Micro Devices',
    score: 75.0,
    raw_return: -0.03,
    volume_z: 1.5,
    volatility_pct: 0.30,
    is_low_liquidity: false,
    trend_quality: 0.62,
    theme_alpha: -0.01,
    theme_beta: 1.05,
    up_capture: 1.02,
    down_capture: 1.1,
    capture_spread: -8,
    is_fallback: true,
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
    expect(fetchEventStocks).toHaveBeenCalledWith('robotics_ai', 20);
  });

  it('랭킹 행을 클릭하면 /chainsight/<symbol> 으로 이동하는 링크를 렌더한다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[0]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    const link = screen.getByRole('link', { name: /NVDA/ });
    expect(link).toHaveAttribute('href', '/chainsight/NVDA');
  });

  it('헤더 행에 3개 지표 라벨(추세강도, 그룹 민감도, 주도우위)을 표시한다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[0]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    expect(screen.getByText('추세강도')).toBeInTheDocument();
    expect(screen.getByText('그룹 민감도')).toBeInTheDocument();
    expect(screen.getByText('주도우위')).toBeInTheDocument();
  });

  it('헤더 행에 각 지표의 MetricInfoPopover 트리거가 있다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[0]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    expect(screen.getByTestId('metric-popover-trend_quality')).toBeInTheDocument();
    expect(screen.getByTestId('metric-popover-theme_beta')).toBeInTheDocument();
    expect(screen.getByTestId('metric-popover-capture_spread')).toBeInTheDocument();
  });

  it('헤더 추가 후에도 종목 링크 드릴다운이 정상 동작한다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue(mockStocks);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    const nvdaLink = screen.getByRole('link', { name: /NVDA/ });
    expect(nvdaLink).toHaveAttribute('href', '/chainsight/NVDA');
    const amdLink = screen.getByRole('link', { name: /AMD/ });
    expect(amdLink).toHaveAttribute('href', '/chainsight/AMD');
  });

  // ── Slice 3: chevron expand/collapse ──────────────────────────────────────

  function isInsideLink(element: HTMLElement): boolean {
    let node: HTMLElement | null = element;
    while (node) {
      if (node.tagName === 'A') return true;
      node = node.parentElement;
    }
    return false;
  }

  it('각 행에 상세 펼치기 chevron 버튼이 있다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue(mockStocks);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    expect(screen.getByRole('button', { name: 'NVDA 상세 펼치기' })).toBeInTheDocument();
  });

  it('기본 상태에서 보조 패널이 숨겨져 있다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[0]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    expect(screen.queryByText('관계 그래프 열기')).not.toBeInTheDocument();
  });

  it('chevron 클릭 시 보조 패널이 나타난다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[0]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    fireEvent.click(screen.getByRole('button', { name: 'NVDA 상세 펼치기' }));
    expect(screen.getByText('관계 그래프 열기')).toBeInTheDocument();
  });

  it('chevron 두 번 클릭 시 보조 패널이 다시 사라진다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[0]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    const btn = screen.getByRole('button', { name: 'NVDA 상세 펼치기' });
    fireEvent.click(btn);
    expect(screen.getByText('관계 그래프 열기')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'NVDA 상세 접기' }));
    expect(screen.queryByText('관계 그래프 열기')).not.toBeInTheDocument();
  });

  it('여러 행의 펼침 상태는 독립적이다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue(mockStocks);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    // NVDA 펼치기
    fireEvent.click(screen.getByRole('button', { name: 'NVDA 상세 펼치기' }));
    // NVDA 패널이 열림
    expect(screen.getByText('관계 그래프 열기')).toBeInTheDocument();
    // AMD 버튼은 여전히 '펼치기' 상태
    expect(screen.getByRole('button', { name: 'AMD 상세 펼치기' })).toBeInTheDocument();
  });

  it('chevron 버튼이 Link(a 태그) 바깥에 있다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[0]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    const chevronBtn = screen.getByRole('button', { name: 'NVDA 상세 펼치기' });
    expect(isInsideLink(chevronBtn)).toBe(false);
  });

  it('보조 패널에 theme_alpha 값이 표시된다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([mockStocks[0]]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('NVDA');
    fireEvent.click(screen.getByRole('button', { name: 'NVDA 상세 펼치기' }));
    // mockStocks[0].theme_alpha = 0.05 → MetricCell renders it
    expect(screen.getByText('0.05')).toBeInTheDocument();
  });

  // ── Slice 4: window selector ──────────────────────────────────────────────

  it('기본 window=20으로 fetchEventStocks를 호출한다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('종목 데이터가 없습니다');
    expect(fetchEventStocks).toHaveBeenCalledWith('semiconductor', 20);
  });

  it('window 셀렉터에 "20일"과 "120일" 버튼이 렌더된다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    expect(screen.getByRole('button', { name: '20일' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '120일' })).toBeInTheDocument();
  });

  it('기본 상태에서 "20일" 버튼이 aria-pressed="true"이다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    expect(screen.getByRole('button', { name: '20일' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '120일' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('window 변경 시 fetchEventStocks가 해당 window로 호출된다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('종목 데이터가 없습니다');

    vi.clearAllMocks();
    vi.mocked(fetchEventStocks).mockResolvedValue([]);

    fireEvent.click(screen.getByRole('button', { name: '120일' }));

    await waitFor(() => {
      expect(fetchEventStocks).toHaveBeenCalledWith('semiconductor', 120);
    });
  });

  it('"120일" 클릭 후 aria-pressed 상태가 전환된다', async () => {
    vi.mocked(fetchEventStocks).mockResolvedValue([]);
    render(<EventRanking theme="semiconductor" />, { wrapper });
    await screen.findByText('종목 데이터가 없습니다');

    fireEvent.click(screen.getByRole('button', { name: '120일' }));

    expect(screen.getByRole('button', { name: '120일' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '20일' })).toHaveAttribute('aria-pressed', 'false');
  });
});
