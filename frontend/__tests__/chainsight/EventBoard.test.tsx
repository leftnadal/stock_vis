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
  Share2: ({ className }: { className?: string }) => <span data-testid="icon-share2" className={className} />,
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

  // ⓑ 가드: 공백·& 포함 다단어 그룹명은 encodeURIComponent로 단일 인코딩 라우팅
  // (raw push 시 '&'가 literal로 남거나 이중 인코딩 → 상세 빈 목록 버그)
  it('카드 클릭 시 공백·& 그룹명을 encodeURIComponent로 라우팅한다 (ⓑ)', async () => {
    const special = [{
      theme: 'Robotics & AI', member_count: 4, avg_return: 0.01,
      avg_score: 58.9, high_attention_count: 1, low_attention_count: 0,
    }];
    vi.mocked(fetchEvents).mockResolvedValue(special);
    render(<EventBoard />, { wrapper });
    const cards = await screen.findAllByRole('button');
    fireEvent.click(cards[0]);
    expect(mockPush).toHaveBeenCalledWith('/chainsight/events/Robotics%20%26%20AI');
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

  // ⓐ 저신뢰 표식: 멤버<3 소규모 그룹은 "표본 작음" 배지(숨기지 않고 신호)
  it('멤버<3 소규모 그룹은 "표본 작음" 저신뢰 표식을 표시한다 (ⓐ)', async () => {
    const small = [{
      theme: 'Lithium & Battery', member_count: 2, avg_return: 0.01,
      avg_score: 63.0, high_attention_count: 0, low_attention_count: 0,
    }];
    vi.mocked(fetchEvents).mockResolvedValue(small);
    render(<EventBoard />, { wrapper });
    await screen.findByRole('button');
    expect(screen.getByText('표본 작음')).toBeInTheDocument();
  });

  it('멤버>=3 그룹은 저신뢰 표식이 없다 (ⓐ 회귀)', async () => {
    vi.mocked(fetchEvents).mockResolvedValue([mockEvents[0]]); // member_count 12
    render(<EventBoard />, { wrapper });
    await screen.findByRole('button');
    expect(screen.queryByText('표본 작음')).not.toBeInTheDocument();
  });

  it('high_attention_count를 카드에 표시한다', async () => {
    vi.mocked(fetchEvents).mockResolvedValue([mockEvents[0]]);
    render(<EventBoard />, { wrapper });
    await screen.findByRole('button');
    expect(screen.getByText('관심↑ 8')).toBeInTheDocument();
  });

  // ON(event_group) 가드: item.name(n3)이 있으면 라벨로 표시하고, theme(slug)로 라우팅.
  // OFF(name 없음)는 위 기존 테스트들이 IDENTICAL 보존을 증명.
  it('ON: item.name(n3)을 라벨로 표시하고 theme(slug)로 라우팅한다', async () => {
    const eg = [{
      theme: 'news-amd-1', name: 'intel devices semiconductor',
      member_count: 5, avg_return: 0.02, avg_score: 70.0,
      high_attention_count: 2, low_attention_count: 1,
    }];
    vi.mocked(fetchEvents).mockResolvedValue(eg);
    render(<EventBoard />, { wrapper });
    const card = await screen.findByRole('button');
    expect(card).toHaveTextContent('intel devices semiconductor'); // n3 표시(섹터 라벨 아님)
    fireEvent.click(card);
    expect(mockPush).toHaveBeenCalledWith('/chainsight/events/news-amd-1'); // slug 키
  });

  // ⑳-2 S4: members 있으면 티커 병기를 주표기로, name은 부제로.
  it('members 티커를 카드 주제목으로 병기한다 (⑳-2 S4)', async () => {
    const eg = [{
      theme: 'news-amd-1', name: 'intel devices semiconductor',
      member_count: 5, members: ['amd', 'intc', 'nvda', 'mu', 'aapl'],
      avg_return: 0.02, avg_score: 70.0, high_attention_count: 2, low_attention_count: 1,
    }];
    vi.mocked(fetchEvents).mockResolvedValue(eg);
    render(<EventBoard />, { wrapper });
    const card = await screen.findByRole('button');
    expect(card).toHaveTextContent('AMD · INTC · NVDA · MU 외 1'); // 티커 병기 주표기
    expect(card).toHaveTextContent('intel devices semiconductor'); // 부제로 유지
  });

  // ⑳-G S4: 위계 강화 — 등락률 최상위 강조, 관심도/종목수 보조 강등(데이터 무변경).
  it('⑳-G S4: 등락률이 최상위 강조 폰트(text-2xl·extrabold)로 렌더된다', async () => {
    vi.mocked(fetchEvents).mockResolvedValue([mockEvents[0]]); // avg_return 0.045
    render(<EventBoard />, { wrapper });
    await screen.findByRole('button');
    const ret = screen.getByText(/4\.50%/);
    expect(ret.className).toMatch(/text-2xl/);
    expect(ret.className).toMatch(/font-extrabold/);
  });

  it('⑳-G S4: 관심도·종목수는 보조 정보로 강등(text-[11px]·gray-400)', async () => {
    vi.mocked(fetchEvents).mockResolvedValue([mockEvents[0]]); // avg_score 85.3, member 12
    render(<EventBoard />, { wrapper });
    await screen.findByRole('button');
    const att = screen.getByText(/관심도 85\.3/);
    expect(att.className).toMatch(/text-\[11px\]/);
    expect(att.className).toMatch(/text-gray-400/);
    const cnt = screen.getByText('12개 종목');
    expect(cnt.className).toMatch(/text-gray-400/);
  });

  it('⑳-G S4: members 티커 주표기가 강조(font-bold·text-base)로 렌더된다', async () => {
    const eg = [{
      theme: 'news-amd-1', name: 'intel semiconductor',
      member_count: 5, members: ['amd', 'intc', 'nvda'],
      avg_return: 0.02, avg_score: 70.0, high_attention_count: 2, low_attention_count: 1,
    }];
    vi.mocked(fetchEvents).mockResolvedValue(eg);
    render(<EventBoard />, { wrapper });
    await screen.findByRole('button');
    const title = screen.getByText(/AMD · INTC · NVDA/);
    expect(title.className).toMatch(/font-bold/);
    expect(title.className).toMatch(/text-base/);
  });

  // A-1 가드: 강등 이동된 관계 그래프가 보드(Chain Sight 홈)에서 도달 가능해야 함(고아 방지).
  it('보드에 /chainsight/market-graph 진입 링크를 노출한다 (A-1)', async () => {
    vi.mocked(fetchEvents).mockResolvedValue([mockEvents[0]]);
    render(<EventBoard />, { wrapper });
    const link = await screen.findByRole('link', { name: /전체 관계 그래프 보기/ });
    expect(link).toHaveAttribute('href', '/chainsight/market-graph');
  });
});
