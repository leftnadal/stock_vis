/**
 * "오늘 시장의 이야기" 피드 (R2-S2 + S3-1 + S3-1B) — 배경 접기(D-S3-7) 포함.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { MarketStoryCard, MarketStoryFeedResponse } from '@/types/chainsight';

vi.mock('@/services/chainsightService', () => ({
  fetchMarketStoryFeed: vi.fn(),
}));

import { fetchMarketStoryFeed } from '@/services/chainsightService';
import MarketStoryFeed from '@/components/chainsight/story/MarketStoryFeed';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const secCard: MarketStoryCard = {
  type: 'new_sec', kind: 'sec_evidence', symbol_a: 'MRVL', symbol_b: 'GOOGL',
  relation_type: 'PARTNER_WITH', item_code: '1.01', occurred_on: '2026-08-19',
  days_since: 14, companions: [], is_group: false, story_id: 'sec1',
  title: 'MRVL, GOOGL와 중요 계약 체결 공시', members: ['GOOGL', 'MRVL'],
  window_label: '30일 내 신규 공시',
  evidence: [{ kind: '8k', ref: 'acc-1', title: 'MRVL, GOOGL와 중요 계약 체결 공시', url: null, date: '2026-08-19' }],
};
const spikeCard: MarketStoryCard = {
  type: 'daily_spike', kind: 'co_mention', symbol_a: 'ORCL', symbol_b: 'PANW',
  count: 13, max_mentions: 13, occurred_on: '2026-08-21', days_since: 12,
  companions: ['TJX'], companions_outside: ['TJX'], is_group: true,
  members: ['ORCL', 'PANW', 'TJX'],
  pairs: [{ symbol_a: 'ORCL', symbol_b: 'PANW', count: 13 }, { symbol_a: 'PANW', symbol_b: 'TJX', count: 12 }],
  window_label: '14일 중 이 하루', story_id: 'spike1',
  title: '오라클·팔로알토 클라우드 계약',
  evidence: [{ kind: 'article', ref: 'cne:1', title: '오라클·팔로알토 클라우드 계약', url: null, date: '2026-08-21' }],
};
function weekly(n: number, titleNull = false): MarketStoryCard {
  return {
    type: 'weekly_active', kind: 'co_mention', symbol_a: `A${n}`, symbol_b: `B${n}`,
    count: 30 - n, occurred_on: '2026-08-31', days_since: 2, companions: [], companions_outside: [],
    is_group: false, members: [`A${n}`, `B${n}`], window_label: '최근 7일 활동',
    story_id: `wk${n}`, title: titleNull ? null : `주간 기사 ${n}`, evidence: [],
  };
}

function feed(events: MarketStoryCard[], steady: MarketStoryCard[]): MarketStoryFeedResponse {
  const cards = [...events, ...steady];
  const by_type = {
    new_sec: cards.filter((c) => c.type === 'new_sec').length,
    daily_spike: cards.filter((c) => c.type === 'daily_spike').length,
    weekly_active: steady.length,
  };
  return {
    as_of: '2026-09-02', has_event: events.length > 0,
    summary: by_type,
    meta: { as_of: '2026-09-02', new_today: 1, stories: cards.length, by_type },
    total: cards.length, cards,
  };
}

const cardEls = () => screen.queryAllByTestId('market-story-card');

describe('MarketStoryFeed 헤더(D-S3-6 잠금)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('부제 = "오늘 새로 온 것 {n} · 전체 {N}"(D-S3-6 유지·회귀)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([secCard, spikeCard], [weekly(1)]));
    render(<MarketStoryFeed />, { wrapper });
    expect(await screen.findByText('오늘 새로 온 것 1 · 전체 3')).toBeInTheDocument();
    expect(screen.queryByText(/최근 \d+일의 이야기/)).not.toBeInTheDocument();
  });
});

describe('D-S3-7 배경 접기', () => {
  beforeEach(() => vi.clearAllMocks());

  it('F.1 사건 카드 있으면 weekly_active는 접힘 줄로만 노출(카드 아님)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([secCard, spikeCard], [weekly(1), weekly(2), weekly(3)]));
    render(<MarketStoryFeed />, { wrapper });
    await screen.findByTestId('steady-fold');
    // 카드는 사건 2장(new_sec·daily_spike)뿐
    const cards = cardEls();
    expect(cards).toHaveLength(2);
    expect(cards.some((c) => c.getAttribute('data-card-type') === 'weekly_active')).toBe(false);
    // 접힘 줄이 m쌍을 말한다
    expect(screen.getByTestId('steady-fold-toggle')).toHaveTextContent('이번 주 꾸준한 흐름 3쌍');
    expect(screen.getByTestId('steady-fold-toggle')).toHaveTextContent('펼치기');
    // 접힌 상태엔 줄 목록 없음
    expect(screen.queryByTestId('steady-line-list')).not.toBeInTheDocument();
  });

  it('F.2 펼치기 클릭 → 줄 목록 렌더(카드 컴포넌트 미사용)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([secCard, spikeCard], [weekly(1), weekly(2)]));
    render(<MarketStoryFeed />, { wrapper });
    fireEvent.click(await screen.findByTestId('steady-fold-toggle'));
    const list = screen.getByTestId('steady-line-list');
    expect(list).toBeInTheDocument();
    expect(screen.getAllByTestId('steady-line')).toHaveLength(2);
    // 줄 목록은 카드 컴포넌트를 쓰지 않는다 → 카드 수는 여전히 사건 2장
    expect(cardEls()).toHaveLength(2);
    // 줄 = 종목쌍·언급 수·날짜만
    const first = screen.getAllByTestId('steady-line')[0];
    expect(first).toHaveTextContent('A1');
    expect(first).toHaveTextContent('29회');
    expect(first).toHaveTextContent('2026-08-31');
    // 칩·근거 수 없음
    expect(first).not.toHaveTextContent('근거');
    expect(first).not.toHaveTextContent('함께:');
  });

  it('F.5 펼침 상태는 리마운트 후 초기화된다(저장 안 함)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([secCard], [weekly(1), weekly(2)]));
    const { unmount } = render(<MarketStoryFeed />, { wrapper });
    fireEvent.click(await screen.findByTestId('steady-fold-toggle'));
    expect(screen.getByTestId('steady-line-list')).toBeInTheDocument();
    unmount();
    render(<MarketStoryFeed />, { wrapper });
    await screen.findByTestId('steady-fold-toggle');
    // 다시 접힌 채로 열림
    expect(screen.queryByTestId('steady-line-list')).not.toBeInTheDocument();
  });

  it('steady가 0이면 접힘 줄 없음(사건만)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([secCard, spikeCard], []));
    render(<MarketStoryFeed />, { wrapper });
    await screen.findAllByTestId('market-story-card');
    expect(screen.queryByTestId('steady-fold')).not.toBeInTheDocument();
  });
});

describe('D-S3-7 조용한 날(사건 0)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('F.3 사건 0 → 배경 3장 펴짐 + "오늘은 조용합니다" 문구', async () => {
    const steady = [weekly(1), weekly(2), weekly(3), weekly(4), weekly(5)];
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([], steady));
    render(<MarketStoryFeed />, { wrapper });
    expect(await screen.findByTestId('quiet-note')).toHaveTextContent(
      '오늘은 조용합니다 — 이번 주 흐름만 보여드립니다',
    );
    // 상위 3장 카드
    expect(cardEls()).toHaveLength(3);
    // 나머지 2쌍은 접힘 줄
    expect(screen.getByTestId('steady-fold-toggle')).toHaveTextContent('이번 주 꾸준한 흐름 2쌍');
  });

  it('조용한 날 steady ≤ 3이면 접힘 줄 없이 전부 카드', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([], [weekly(1), weekly(2)]));
    render(<MarketStoryFeed />, { wrapper });
    await screen.findByTestId('quiet-note');
    expect(cardEls()).toHaveLength(2);
    expect(screen.queryByTestId('steady-fold')).not.toBeInTheDocument();
  });

  it('빈 화면을 만들지 않는다(사건0·steady0 = 빈 상태 메시지)', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([], []));
    render(<MarketStoryFeed />, { wrapper });
    expect(await screen.findByText('아직 관찰된 이야기가 없습니다')).toBeInTheDocument();
  });
});

describe('이벤트 카드(회귀 — 사건 카드는 항상 펴짐)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('8-K 카드: 템플릿 제목 + item + window_label', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([secCard, spikeCard], [weekly(1)]));
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    const sec = cards.find((c) => c.getAttribute('data-card-type') === 'new_sec')!;
    expect(sec).toHaveTextContent('MRVL, GOOGL와 중요 계약 체결 공시');
    expect(sec).toHaveTextContent('SEC 8-K item 1.01 · 2026-08-19');
    expect(sec).toHaveTextContent('30일 내 신규 공시');
  });

  it('묶음 카드: 제목 인용 + 멤버 + data-story-id + 관계 아님 캡션', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([secCard, spikeCard], [weekly(1)]));
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    const spike = cards.find((c) => c.getAttribute('data-card-type') === 'daily_spike')!;
    expect(spike).toHaveTextContent('오라클·팔로알토 클라우드 계약');
    expect(spike).toHaveTextContent('ORCL · PANW · TJX');
    expect(spike).toHaveAttribute('data-story-id', 'spike1');
    expect(spike).toHaveTextContent('관계 아님 · 동시 언급');
    expect(spike).toHaveAttribute('href', '/chainsight/mindmap?symbol=ORCL');
  });

  it('배수·평소대비 표기 절대 없음', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([secCard, spikeCard], [weekly(1)]));
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    for (const c of cards) {
      expect(c).not.toHaveTextContent('평소 대비');
      expect(c.textContent ?? '').not.toMatch(/\d+배/);
    }
  });

  it('조용한 날 peek 카드: 제목 없으면 "근거 기사 없음" 정직 표기', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([], [weekly(1, true), weekly(2), weekly(3)]));
    render(<MarketStoryFeed />, { wrapper });
    const cards = await screen.findAllByTestId('market-story-card');
    expect(cards[0]).toHaveTextContent('근거 기사 없음 · 언급 수만 집계');
  });

  it('마인드맵 링크 상시 노출', async () => {
    vi.mocked(fetchMarketStoryFeed).mockReturnValue(new Promise(() => {}));
    render(<MarketStoryFeed />, { wrapper });
    expect(screen.getByRole('link', { name: '업종별 보기 (마인드맵)' })).toHaveAttribute(
      'href', '/chainsight/mindmap',
    );
  });
});

describe('상태 회귀(K 복원)', () => {
  beforeEach(() => vi.clearAllMocks());

  // S3-1에 있었으나 S3-1B 통합 과정에서 소실된 회귀 — 구현 무변경, 잠그는 테스트.
  it('fetch 실패(isError): "다시 시도" 버튼 + 마인드맵 링크 유지', async () => {
    vi.mocked(fetchMarketStoryFeed).mockRejectedValue(new Error('network'));
    render(<MarketStoryFeed />, { wrapper });
    expect(await screen.findByText('데이터를 불러올 수 없습니다')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '다시 시도' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '업종별 보기 (마인드맵)' })).toHaveAttribute(
      'href', '/chainsight/mindmap',
    );
  });

  it('배지 색 계열 구분(복원): 사건=blue/amber, 배경=gray', async () => {
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([secCard, spikeCard], [weekly(1)]));
    const { unmount } = render(<MarketStoryFeed />, { wrapper });
    await screen.findAllByTestId('market-story-card');
    expect(screen.getByText('신규 연결 · 8-K').className).toMatch(/blue/);
    expect(screen.getByText('일간 급등').className).toMatch(/amber/);
    unmount();
    // 배경 배지는 조용한 날(peek 카드)에서 확인
    vi.mocked(fetchMarketStoryFeed).mockResolvedValue(feed([], [weekly(1)]));
    render(<MarketStoryFeed />, { wrapper });
    await screen.findAllByTestId('market-story-card');
    expect(screen.getByText('이번 주 활발').className).toMatch(/gray/);
  });
});
