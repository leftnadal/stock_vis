/**
 * "오늘 시장의 이야기" 피드 (R2-S2 + S3-1) — 헤더 정직화 + 묶음 카드 + 제목 인용 + 정직 캡션.
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
    summary: { new_sec: 1, daily_spike: 1, weekly_active: 1 },
    meta: { as_of: '2026-09-02', new_today: 1, stories: 3, by_type: { new_sec: 1, daily_spike: 1, weekly_active: 1 } },
    total: 3,
    cards: [
      {
        type: 'new_sec', kind: 'sec_evidence', symbol_a: 'MRVL', symbol_b: 'GOOGL',
        relation_type: 'PARTNER_WITH', item_code: '1.01', occurred_on: '2026-08-19',
        days_since: 14, companions: [], is_group: false,
        story_id: '832af17221', story_key: 'new_sec:GOOGL-MRVL:2026-08-19',
        title: 'MRVL, GOOGL와 중요 계약 체결 공시', members: ['GOOGL', 'MRVL'],
        window_label: '30일 내 신규 공시',
        evidence: [{ kind: '8k', ref: 'acc-1', title: 'MRVL, GOOGL와 중요 계약 체결 공시', url: null, date: '2026-08-19' }],
      },
      {
        type: 'daily_spike', kind: 'co_mention', symbol_a: 'ORCL', symbol_b: 'PANW',
        count: 13, max_mentions: 13, occurred_on: '2026-08-21', days_since: 12,
        companions: ['TJX', 'BLK', 'ROST', 'CRM'], companions_outside: ['TJX', 'BLK', 'ROST', 'CRM'],
        is_group: true, members: ['BLK', 'ORCL', 'PANW', 'ROST', 'TJX'],
        pairs: [
          { symbol_a: 'ORCL', symbol_b: 'PANW', count: 13 },
          { symbol_a: 'PANW', symbol_b: 'TJX', count: 12 },
          { symbol_a: 'ORCL', symbol_b: 'ROST', count: 6 },
        ],
        window_label: '14일 중 이 하루',
        story_id: '4b359d1ac0', story_key: 'daily_spike:BLK-ORCL-PANW-ROST-TJX:2026-08-21',
        title: '오라클·팔로알토 클라우드 계약',
        evidence: [{ kind: 'article', ref: 'cne:1', title: '오라클·팔로알토 클라우드 계약', url: 'http://n/1', date: '2026-08-21T13:00:00+00:00' }],
      },
      {
        type: 'weekly_active', kind: 'co_mention', symbol_a: 'JPM', symbol_b: 'BAC',
        count: 27, occurred_on: '2026-08-31', days_since: 2, companions: [], companions_outside: [],
        is_group: false, members: ['BAC', 'JPM'], window_label: '최근 7일 활동',
        story_id: 'e98a0a8bf2', story_key: 'weekly_active:BAC-JPM:2026-08-31',
        title: null, evidence: [],
      },
    ],
    ...partial,
  };
}

const byType = (t: string) => (els: HTMLElement[]) => els.find((c) => c.getAttribute('data-card-type') === t)!;

describe('MarketStoryFeed 헤더(A-5 정직화)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('제목은 단일 창 N을 주장하지 않는다("최근 N일" 금지)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    expect(await screen.findByText('오늘 시장의 이야기')).toBeInTheDocument();
    expect(screen.queryByText(/최근 \d+일의 이야기/)).not.toBeInTheDocument();
  });

  it('has_event=true 부제 = "오늘 새로 온 것 {n} · 전체 {N}"(창 미표기)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    expect(await screen.findByText('오늘 새로 온 것 1 · 전체 3')).toBeInTheDocument();
  });

  it('has_event=false 부제 = 조용한 날 카피(정문 무공허)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(
      feed({ has_event: false, meta: { as_of: '2026-09-02', new_today: 0, stories: 5, by_type: { new_sec: 0, daily_spike: 0, weekly_active: 5 } } }),
    );
    render(<MarketStoryFeed />, { wrapper });
    expect(
      await screen.findByText('오늘은 큰 사건이 없어요 — 꾸준히 활발한 이야기들'),
    ).toBeInTheDocument();
  });

  it('마인드맵 링크 상시 노출(로딩 상태)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockReturnValue(new Promise(() => {}));
    render(<MarketStoryFeed />, { wrapper });
    expect(screen.getByRole('link', { name: '업종별 보기 (마인드맵)' })).toHaveAttribute(
      'href', '/chainsight/mindmap',
    );
  });
});

describe('MarketStoryFeed 카드(S3-1 묶음·제목·정직)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('카드 3장 렌더 + 각 카드에 data-story-id 부여(S3-4 앵커)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    expect(cards).toHaveLength(3);
    expect(byType('daily_spike')(cards)).toHaveAttribute('data-story-id', '4b359d1ac0');
  });

  it('묶음 카드: 제목(기사 원문 인용) + 멤버 라인 + N쌍/최대 M회', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const spike = byType('daily_spike')(await screen.findAllByTestId('market-story-card'));
    expect(spike).toHaveTextContent('오라클·팔로알토 클라우드 계약'); // 제목 인용
    expect(spike).toHaveTextContent('BLK · ORCL · PANW · ROST · TJX'); // 멤버 라인
    expect(spike).toHaveTextContent('3쌍 · 최대 13회'); // 묶음 메타
  });

  it('제목 없는 co_mention 카드는 "근거 기사 없음 · 언급 수만 집계"로 정직 표기', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const steady = byType('weekly_active')(await screen.findAllByTestId('market-story-card'));
    expect(steady).toHaveTextContent('근거 기사 없음 · 언급 수만 집계');
  });

  it('8-K 카드: 공시 사실 제목 템플릿 + item + 발생일', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const sec = byType('new_sec')(await screen.findAllByTestId('market-story-card'));
    expect(sec).toHaveTextContent('MRVL, GOOGL와 중요 계약 체결 공시');
    expect(sec).toHaveTextContent('SEC 8-K item 1.01 · 2026-08-19');
  });

  it('근거 수를 표기한다(evidence 있을 때)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const spike = byType('daily_spike')(await screen.findAllByTestId('market-story-card'));
    expect(spike).toHaveTextContent('근거 1');
  });

  it('배수·평소대비 표기 절대 없음(정직성 유지)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    for (const c of cards) {
      expect(c).not.toHaveTextContent('평소 대비');
      expect(c.textContent ?? '').not.toMatch(/\d+배/);
    }
  });

  it('co_mention 카드에만 "관계 아님 · 동시 언급" 캡션', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    expect(byType('daily_spike')(cards)).toHaveTextContent('관계 아님 · 동시 언급');
    expect(byType('weekly_active')(cards)).toHaveTextContent('관계 아님 · 동시 언급');
    expect(byType('new_sec')(cards)).not.toHaveTextContent('관계 아님');
  });

  it('딥링크 → 마인드맵 ?symbol=symbol_a (기존 동작 보존)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const spike = byType('daily_spike')(await screen.findAllByTestId('market-story-card'));
    expect(spike).toHaveAttribute('href', '/chainsight/mindmap?symbol=ORCL');
  });

  it('companions_outside 칩 렌더(묶음 멤버 외 동반)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const spike = byType('daily_spike')(await screen.findAllByTestId('market-story-card'));
    expect(spike).toHaveTextContent('함께:');
    expect(spike).toHaveTextContent('CRM');
  });

  it('카드가 자기 관측 창을 말한다(window_label)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    expect(byType('daily_spike')(cards)).toHaveTextContent('14일 중 이 하루');
    expect(byType('new_sec')(cards)).toHaveTextContent('30일 내 신규 공시');
    expect(byType('weekly_active')(cards)).toHaveTextContent('최근 7일 활동');
  });

  it('사건→배경 전환점에 "여기부터 잔잔한 흐름" 구분선', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    const divider = await screen.findByTestId('steady-divider');
    expect(divider).toHaveTextContent('여기부터 잔잔한 흐름');
  });

  it('사건 카드가 없으면(전부 steady) 구분선 없음', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(
      feed({
        has_event: false,
        meta: { as_of: '2026-09-02', new_today: 0, stories: 1, by_type: { new_sec: 0, daily_spike: 0, weekly_active: 1 } },
        cards: [
          {
            type: 'weekly_active', kind: 'co_mention', symbol_a: 'JPM', symbol_b: 'BAC',
            count: 27, occurred_on: '2026-08-31', days_since: 2, companions: [], companions_outside: [],
            is_group: false, members: ['BAC', 'JPM'], window_label: '최근 7일 활동',
            story_id: 'e98a0a8bf2', title: null, evidence: [],
          },
        ],
        total: 1,
      }),
    );
    render(<MarketStoryFeed />, { wrapper });
    await screen.findAllByTestId('market-story-card');
    expect(screen.queryByTestId('steady-divider')).not.toBeInTheDocument();
  });

  it('배지 색 계열 구분(사건 vs steady)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed());
    render(<MarketStoryFeed />, { wrapper });
    await screen.findAllByTestId('market-story-card');
    expect(screen.getByText('신규 연결 · 8-K').className).toMatch(/blue/);
    expect(screen.getByText('일간 급등').className).toMatch(/amber/);
    expect(screen.getByText('이번 주 활발').className).toMatch(/gray/);
  });
});

describe('MarketStoryFeed 상태', () => {
  beforeEach(() => vi.clearAllMocks());

  it('에러 상태: 다시 시도 + 마인드맵 링크 유지', async () => {
    vi.mocked(fetchMarketStoryFeed).mockRejectedValue(new Error('network'));
    render(<MarketStoryFeed />, { wrapper });
    expect(await screen.findByText('데이터를 불러올 수 없습니다')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '업종별 보기 (마인드맵)' })).toBeInTheDocument();
  });

  it('빈 카드 배열이면 빈 상태 메시지', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed({ cards: [], total: 0 }));
    render(<MarketStoryFeed />, { wrapper });
    expect(await screen.findByText('아직 관찰된 이야기가 없습니다')).toBeInTheDocument();
  });
});
