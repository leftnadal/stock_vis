import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EventBoard from '@/components/chainsight/EventBoard';

// Mock fetchEvents
vi.mock('@/services/chainsightService', () => ({
  fetchEvents: vi.fn(),
}));

// Mock router
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock getLabelForTheme
vi.mock('@/constants/eventThemes', () => ({
  getLabelForTheme: (theme: string) => ({
    ko: theme === 'semiconductor' ? '반도체' : theme,
    icon: 'Tag',
  }),
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Tag: ({ className }: { className?: string }) => <span data-testid="icon-tag" className={className} />,
  Cpu: ({ className }: { className?: string }) => <span data-testid="icon-cpu" className={className} />,
}));

import { fetchEvents } from '@/services/chainsightService';

const mockEvents = [
  {
    theme: 'semiconductor',
    member_count: 12,
    avg_return: 0.045,
    avg_score: 85.3,
    high_attention_count: 8,
    low_attention_count: 2,
  },
  {
    theme: 'clean_energy',
    member_count: 6,
    avg_return: -0.012,
    avg_score: 62.1,
    high_attention_count: 3,
    low_attention_count: 1,
  },
];

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('EventBoard', () => {
  beforeEach(() => vi.clearAllMocks());

  it('로딩 상태를 표시한다', async () => {
    vi.mocked(fetchEvents).mockReturnValue(new Promise(() => {}));
    render(<EventBoard />, { wrapper });
    expect(screen.getByText('로딩 중...')).toBeInTheDocument();
  });

  it('avg_score 내림차순으로 카드를 정렬해 렌더링한다', async () => {
    vi.mocked(fetchEvents).mockResolvedValue(mockEvents);
    render(<EventBoard />, { wrapper });
    const cards = await screen.findAllByRole('button');
    // semiconductor(85.3) should come before clean_energy(62.1)
    expect(cards[0]).toHaveTextContent('반도체');
    expect(cards[1]).toHaveTextContent('clean_energy'); // unmapped fallback
  });

  it('카드 클릭 시 /chainsight/events/<theme> 로 라우팅된다', async () => {
    vi.mocked(fetchEvents).mockResolvedValue(mockEvents);
    render(<EventBoard />, { wrapper });
    const cards = await screen.findAllByRole('button');
    fireEvent.click(cards[0]);
    expect(mockPush).toHaveBeenCalledWith('/chainsight/events/semiconductor');
  });

  it('avg_return이 양수면 ▲ 초록색 표시', async () => {
    vi.mocked(fetchEvents).mockResolvedValue([mockEvents[0]]);
    render(<EventBoard />, { wrapper });
    await screen.findByRole('button');
    expect(screen.getByText(/▲/)).toBeInTheDocument();
  });

  it('avg_return이 음수면 ▼ 표시', async () => {
    vi.mocked(fetchEvents).mockResolvedValue([mockEvents[1]]);
    render(<EventBoard />, { wrapper });
    await screen.findByRole('button');
    expect(screen.getByText(/▼/)).toBeInTheDocument();
  });

  it('빈 데이터면 빈 상태 메시지를 표시한다', async () => {
    vi.mocked(fetchEvents).mockResolvedValue([]);
    render(<EventBoard />, { wrapper });
    expect(await screen.findByText('이벤트 데이터가 없습니다')).toBeInTheDocument();
  });

  it('high_attention_count를 카드에 표시한다', async () => {
    vi.mocked(fetchEvents).mockResolvedValue([mockEvents[0]]);
    render(<EventBoard />, { wrapper });
    await screen.findByRole('button');
    expect(screen.getByText('관심↑ 8')).toBeInTheDocument();
  });
});
