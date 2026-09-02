/**
 * "오늘 시장의 이야기" 피드 (R2-S2) — 헤더 2줄 + 마인드맵 링크 상시 노출 + 카드 그리드.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { MarketStoryFeedResponse } from '@/types/chainsight';

vi.mock('@/services/chainsightService', () => ({
  fetchMarketStoryFeed: vi.fn(),
}));

import { fetchMarketStoryFeed } from '@/services/chainsightService';
import MarketStoryFeed from '@/components/chainsight/story/MarketStoryFeed';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function feed(partial: Partial<MarketStoryFeedResponse> = {}): MarketStoryFeedResponse {
  return {
    as_of: '2026-09-02',
    has_event: true,
    summary: { new_sec: 2, daily_spike: 8, weekly_active: 20 },
    total: 3,
    cards: [
      {
        type: 'new_sec', kind: 'sec_evidence', symbol_a: 'MRVL', symbol_b: 'GOOGL',
        relation_type: 'PARTNER_WITH', item_code: '1.01', occurred_on: '2026-08-19',
        days_since: 14, companions: [],
      },
      {
        type: 'daily_spike', kind: 'co_mention', symbol_a: 'ORCL', symbol_b: 'PANW',
        count: 13, occurred_on: '2026-08-21', days_since: 12,
        companions: ['TJX', 'BLK', 'ROST', 'CRM'],
      },
      {
        type: 'weekly_active', kind: 'co_mention', symbol_a: 'JPM', symbol_b: 'BAC',
        count: 27, occurred_on: '2026-08-31', days_since: 2, companions: [],
      },
    ],
    ...partial,
  };
}

describe('MarketStoryFeed', () => {
  beforeEach(() => vi.clearAllMocks());

  it('로딩 상태를 표시하되 마인드맵 링크는 상시 노출한다', async () => {
    vi.mocked(fetchMarketStoryFeed).mockReturnValue(new Promise(() => {}));
    render(<MarketStoryFeed />, { wrapper });
    expect(screen.getByText('로딩 중...')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '업종별 보기 (마인드맵)' })).toHaveAttribute(
      'href',
      '/chainsight/mindmap',
    );
  });

  it('has_event=true: 부제 = "{as_of} · 급증 N건 · 신규 연결 N건"', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    expect(screen.getByText('오늘 시장의 이야기')).toBeInTheDocument();
    expect(
      await screen.findByText('2026-09-02 · 급증 8건 · 신규 연결 2건'),
    ).toBeInTheDocument();
  });

  // 목업 준거 ⑷(정문 무공허): has_event=false 는 공허 카피 금지, steady 카피로 대체.
  it('has_event=false: 부제 = "오늘은 큰 사건이 없어요 — 꾸준히 활발한 이야기들"', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(
      feed({ has_event: false, summary: { new_sec: 0, daily_spike: 0, weekly_active: 5 } }),
    );
    render(<MarketStoryFeed />, { wrapper });
    expect(
      await screen.findByText('오늘은 큰 사건이 없어요 — 꾸준히 활발한 이야기들'),
    ).toBeInTheDocument();
  });

  it('마인드맵 링크를 헤더 우상단에 항상 노출한다 (⑵)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const link = await screen.findByRole('link', { name: '업종별 보기 (마인드맵)' });
    expect(link).toHaveAttribute('href', '/chainsight/mindmap');
  });

  it('카드 3장을 유형별로 렌더한다', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    expect(cards).toHaveLength(3);
  });

  it('카드 클릭(딥링크) → 마인드맵 ?symbol=symbol_a 로 라우팅된다 (⑶)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    // 정렬 순서(BE)와 무관하게 daily_spike(ORCL) 카드를 찾는다.
    const orcl = cards.find((c) => c.textContent?.includes('ORCL'));
    expect(orcl).toHaveAttribute('href', '/chainsight/mindmap?symbol=ORCL');
  });

  it('co_mention 카드(daily_spike·weekly_active)에는 "관계 아님 · 동시 언급" 캡션이 있다 (규칙 3)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    const spike = cards.find((c) => c.getAttribute('data-card-type') === 'daily_spike')!;
    const steady = cards.find((c) => c.getAttribute('data-card-type') === 'weekly_active')!;
    expect(spike).toHaveTextContent('관계 아님 · 동시 언급');
    expect(steady).toHaveTextContent('관계 아님 · 동시 언급');
  });

  it('new_sec 카드(sec_evidence)에는 "관계 아님" 캡션이 없다 (규칙 3)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    const sec = cards.find((c) => c.getAttribute('data-card-type') === 'new_sec')!;
    expect(sec).not.toHaveTextContent('관계 아님');
  });

  it('daily_spike 카드는 "평소 대비"·"배수" 문구를 절대 포함하지 않는다 (절대량+발생일만)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    const spike = cards.find((c) => c.getAttribute('data-card-type') === 'daily_spike')!;
    expect(spike).not.toHaveTextContent('평소 대비');
    expect(spike).not.toHaveTextContent('배수');
    expect(spike).toHaveTextContent('13회 함께 언급 · 2026-08-21');
  });

  it('daily_spike 카드의 companions는 칩으로 렌더된다', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    const spike = cards.find((c) => c.getAttribute('data-card-type') === 'daily_spike')!;
    expect(spike).toHaveTextContent('함께:');
    expect(spike).toHaveTextContent('TJX');
    expect(spike).toHaveTextContent('BLK');
  });

  it('new_sec 카드는 relation_type 표시어(파트너) + item_code + occurred_on을 렌더한다', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    const sec = cards.find((c) => c.getAttribute('data-card-type') === 'new_sec')!;
    expect(sec).toHaveTextContent('파트너');
    expect(sec).toHaveTextContent('SEC 8-K item 1.01 · 2026-08-19');
  });

  it('weekly_active 카드는 "이번 주 N회 함께 언급 · 최근 N일 전"을 렌더한다', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    const steady = cards.find((c) => c.getAttribute('data-card-type') === 'weekly_active')!;
    expect(steady).toHaveTextContent('이번 주 27회 함께 언급 · 최근 2일 전');
  });

  // 목업 준거 ⑷: 배지 색 계열 구분 — 사건(new_sec·daily_spike) vs steady(weekly_active).
  it('사건 카드 배지와 steady 카드 배지는 서로 다른 색 클래스를 쓴다 (⑷)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    await screen.findAllByTestId('market-story-card');
    expect(screen.getByText('신규 연결 · 8-K').className).toMatch(/blue/);
    expect(screen.getByText('일간 급등').className).toMatch(/amber/);
    expect(screen.getByText('이번 주 활발').className).toMatch(/gray/);
  });

  it('에러 상태: 다시 시도 버튼', async () => {
    vi.mocked(fetchMarketStoryFeed).mockRejectedValue(new Error('network'));
    render(<MarketStoryFeed />, { wrapper });
    expect(await screen.findByText('데이터를 불러올 수 없습니다')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '업종별 보기 (마인드맵)' })).toBeInTheDocument();
  });

  it('빈 카드 배열이면 빈 상태 메시지를 표시한다', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed({ cards: [], total: 0 }));
    render(<MarketStoryFeed />, { wrapper });
    expect(await screen.findByText('아직 관찰된 이야기가 없습니다')).toBeInTheDocument();
  });
});
