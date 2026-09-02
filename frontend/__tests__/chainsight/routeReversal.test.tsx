import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

/**
 * 라우트 토폴로지 가드 — RD3(2026-06-18) → R2-S2(2026-09-02) 역전 누적 반영.
 * - 루트 /chainsight = "오늘 시장의 이야기" 피드 (R2-S2, 이벤트 보드·그래프 아님)
 * - /chainsight/feed = 피드 전용 라우트(동일 컴포넌트)
 * - /chainsight/events = 이벤트 보드 직접 렌더(강등 이동, redirect 아님 — 원클릭 접근 유지)
 * - /chainsight/market-graph = 강등 이동된 마켓 그래프
 * 자식 컴포넌트/훅은 sentinel로 대체 — 라우트가 "무엇을 렌더하는지"만 검증.
 */

// next/navigation: redirect(events) + useSearchParams/useRouter(market-graph)
const redirectMock = vi.fn();
vi.mock('next/navigation', () => ({
  redirect: (url: string) => redirectMock(url),
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn() }),
}));

// 보드 sentinel
vi.mock('@/components/chainsight/EventBoard', () => ({
  default: () => <div data-testid="event-board" />,
}));

// 피드 sentinel (R2-S2 신규 랜딩)
vi.mock('@/components/chainsight/story/MarketStoryFeed', () => ({
  default: () => <div data-testid="market-story-feed" />,
}));

// 그룹 상세 sentinel — theme prop을 노출해 디코딩 검증
vi.mock('@/components/chainsight/EventRanking', () => ({
  default: ({ theme }: { theme: string }) => <div data-testid="event-ranking">{theme}</div>,
}));

// 그래프 화면 sentinel + 주변 컴포넌트/훅
vi.mock('@/components/chainsight/MarketGraphCanvas', () => ({
  default: () => <div data-testid="market-graph-canvas" />,
}));
vi.mock('@/components/chainsight/SectorBar', () => ({ default: () => <div /> }));
vi.mock('@/components/chainsight/RelationFilterChips', () => ({ default: () => <div /> }));
vi.mock('@/components/chainsight/ExplorationTrail', () => ({ default: () => <div /> }));
vi.mock('@/components/chainsight/RelationCardPanel', () => ({ default: () => <div /> }));
vi.mock('@/components/chainsight/ChainStoryFeed', () => ({ default: () => <div /> }));
vi.mock('@/hooks/useMarketView', () => ({
  useSeedData: () => ({ data: { seeds: [], sector_summary: [{ sector: 'Tech' }] }, isLoading: false }),
}));
vi.mock('@/lib/stores/explorationStore', () => ({
  useExplorationStore: () => ({ selectedSector: null, initializeFocusExploration: vi.fn() }),
}));

describe('라우트 역전 (RD3 → R2-S2)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('루트 /chainsight 가 "오늘 시장의 이야기" 피드를 렌더한다 (이벤트 보드·그래프 아님)', async () => {
    const Page = (await import('@/app/chainsight/page')).default;
    render(<Page />);
    expect(screen.getByTestId('market-story-feed')).toBeInTheDocument();
    expect(screen.queryByTestId('event-board')).not.toBeInTheDocument();
    expect(screen.queryByTestId('market-graph-canvas')).not.toBeInTheDocument();
  });

  it('/chainsight/feed 가 동일 피드 컴포넌트를 렌더한다', async () => {
    const Page = (await import('@/app/chainsight/feed/page')).default;
    render(<Page />);
    expect(screen.getByTestId('market-story-feed')).toBeInTheDocument();
  });

  it('/chainsight/events 는 이벤트 보드를 직접 렌더한다 (redirect 아님 — 원클릭 접근 유지)', async () => {
    const Page = (await import('@/app/chainsight/events/page')).default;
    render(<Page />);
    expect(screen.getByTestId('event-board')).toBeInTheDocument();
    expect(redirectMock).not.toHaveBeenCalled();
  });

  it('/chainsight/market-graph 가 마켓 그래프를 렌더한다 (보드 아님)', async () => {
    const Page = (await import('@/app/chainsight/market-graph/page')).default;
    render(<Page />);
    expect(await screen.findByTestId('market-graph-canvas')).toBeInTheDocument();
    expect(screen.queryByTestId('event-board')).not.toBeInTheDocument();
  });

  // ⓑ 인코딩 정합: 그룹 상세 페이지가 encodeURIComponent된 그룹명을 단일 디코딩해 전달
  describe('/chainsight/events/[theme] 그룹명 인코딩 왕복 (ⓑ)', () => {
    // 공백·& 포함 다단어 7개 + 단어1개(회귀 가드)
    const SPECIAL = [
      'Communication Services', 'Consumer Discretionary', 'Consumer Staples',
      'Real Estate', 'Robotics & AI', 'Lithium & Battery', 'Clean Energy',
    ];
    const PLAIN = ['Technology', 'Energy', 'Semiconductor'];

    it.each(SPECIAL)('encode→route→decode 왕복으로 "%s" 원본 복원', async (theme) => {
      const Page = (await import('@/app/chainsight/events/[theme]/page')).default;
      // EventBoard가 push하는 형태 = encodeURIComponent(theme)
      const routed = encodeURIComponent(theme);
      const el = await Page({ params: Promise.resolve({ theme: routed }) });
      render(el);
      expect(screen.getByTestId('event-ranking')).toHaveTextContent(theme);
    });

    it.each(PLAIN)('단어1개 그룹 "%s" 회귀 없음', async (theme) => {
      const Page = (await import('@/app/chainsight/events/[theme]/page')).default;
      const el = await Page({ params: Promise.resolve({ theme: encodeURIComponent(theme) }) });
      render(el);
      expect(screen.getByTestId('event-ranking')).toHaveTextContent(theme);
    });
  });
});
