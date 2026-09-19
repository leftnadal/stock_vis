import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RecommendationCard } from '@/components/eod/RecommendationCard';
import { pickPerspectiveLine, presentPerspectives } from '@/components/eod/recommendation';
import type { Recommendation } from '@/types/eod';

// (구 RecommendationCardScanner.test — "스캐너 N축 포착"(≥2)·신뢰 라벨은 DASH-RECO R3로 폐기되어 이 파일로 대체)
function rec(overrides: Partial<Recommendation> = {}): Recommendation {
  return {
    rank: 1,
    ticker: 'NVDA',
    company_name: 'NVIDIA',
    signal_tag: 'P1',
    confidence: 'high',
    conf_ver: 1,
    composite_score: 1,
    thesis: '논리',
    perspectives: { technical: null, fundamental: null, news_context: null },
    risk: null,
    ...overrides,
  };
}

describe('RecommendationCard — R3 표시', () => {
  it('#N 순위·신뢰 라벨·강도 spine을 그리지 않는다', () => {
    render(<RecommendationCard rec={rec({ rank: 3 })} axisCategories={['momentum']} />);
    expect(screen.queryByText('#3')).toBeNull();
    expect(screen.queryByText(/신뢰/)).toBeNull();
    expect(screen.queryByRole('meter')).toBeNull();
  });

  it('1축이어도 헤더 N축 배지를 표시한다(스캐너 임계 2와 무관)', () => {
    render(<RecommendationCard rec={rec()} axisCategories={['volume']} />);
    expect(screen.getByText('1축')).toBeInTheDocument();
  });

  it('6칸 pips — 걸린 축 칸만 채운다(위치 = 카테고리 순서)', () => {
    const { container } = render(
      <RecommendationCard rec={rec()} axisCategories={['momentum', 'technical', 'volume']} />,
    );
    const pips = [...container.querySelectorAll('[data-axis]')];
    expect(pips.map((p) => p.getAttribute('data-axis'))).toEqual([
      'momentum', 'volume', 'breakout', 'reversal', 'relation', 'technical',
    ]);
    expect(pips.map((p) => p.getAttribute('data-filled'))).toEqual([
      'true', 'true', 'false', 'false', 'false', 'true',
    ]);
    expect(screen.getByRole('img', { name: /6개 중 3축/ })).toBeInTheDocument();
    expect(screen.getByText('3축')).toBeInTheDocument();
  });

  it('0축 → 축 배지·pips 조용히 생략(정칙 ⑴)', () => {
    const { container } = render(<RecommendationCard rec={rec()} />);
    expect(screen.queryByText(/축$/)).toBeNull();
    expect(container.querySelector('[data-axis]')).toBeNull();
  });

  it('방향 동사·signal_tag는 유지', () => {
    render(<RecommendationCard rec={rec({ composite_score: -1 })} />);
    expect(screen.getByText('매도·회피')).toBeInTheDocument();
    expect(screen.getByText('P1')).toBeInTheDocument();
  });
});

describe('RecommendationCard — P3 관점 한 줄', () => {
  it('fundamental 우선', () => {
    render(
      <RecommendationCard
        rec={rec({ perspectives: { technical: '기술문', fundamental: '펀더문', news_context: '뉴스문' } })}
      />,
    );
    expect(screen.getByTitle('펀더문')).toHaveTextContent('펀더멘털 · 펀더문');
    expect(screen.queryByTitle('기술문')).toBeNull();
  });

  it('fundamental null → technical 폴백', () => {
    render(
      <RecommendationCard
        rec={rec({ perspectives: { technical: '기술문', fundamental: null, news_context: '뉴스문' } })}
      />,
    );
    expect(screen.getByTitle('기술문')).toHaveTextContent('기술 · 기술문');
  });

  it('둘 다 없으면 줄 생략 — "정보 없음" 표기 없음', () => {
    const r = rec({ perspectives: { technical: null, fundamental: '  ', news_context: '뉴스문' } });
    expect(pickPerspectiveLine(r)).toBeNull();
    render(<RecommendationCard rec={r} />);
    expect(screen.queryByTitle('뉴스문')).toBeNull();
    expect(screen.queryByText(/뉴스문/)).toBeNull();
    expect(screen.queryByText(/정보 없음|없음/)).toBeNull();
  });

  it('presentPerspectives = 값 있는 관점만 기술→펀더→뉴스 순', () => {
    const r = rec({ perspectives: { technical: 't', fundamental: null, news_context: 'n' } });
    expect(presentPerspectives(r).map((p) => p.kind)).toEqual(['technical', 'news_context']);
  });
});

describe('RecommendationCard — 진입 동선', () => {
  it('본문 클릭 = onOpen(드로어)', () => {
    const onOpen = vi.fn();
    render(<RecommendationCard rec={rec()} onOpen={onOpen} />);
    fireEvent.click(screen.getByRole('button', { name: /추천 NVDA/ }));
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it('Enter 키로도 연다', () => {
    const onOpen = vi.fn();
    render(<RecommendationCard rec={rec()} onOpen={onOpen} />);
    fireEvent.keyDown(screen.getByRole('button', { name: /추천 NVDA/ }), { key: 'Enter' });
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it('체인사이트 링크 클릭은 본문(드로어)으로 전파하지 않는다', () => {
    const onOpen = vi.fn();
    render(<RecommendationCard rec={rec()} onOpen={onOpen} />);
    const link = screen.getByRole('link', { name: /체인사이트/ });
    expect(link.getAttribute('href')).toBe('/stocks/NVDA?tab=chain-sight');
    fireEvent.click(link);
    expect(onOpen).not.toHaveBeenCalled();
  });

  it('가로 스와이프 뒤 click은 드로어를 열지 않는다', () => {
    const onOpen = vi.fn();
    render(<RecommendationCard rec={rec()} onOpen={onOpen} />);
    const body = screen.getByRole('button', { name: /추천 NVDA/ });
    fireEvent.touchStart(body, { touches: [{ clientX: 0, clientY: 0 }] });
    fireEvent.touchMove(body, { touches: [{ clientX: 40, clientY: 0 }] });
    fireEvent.click(body);
    expect(onOpen).not.toHaveBeenCalled();
  });
});
