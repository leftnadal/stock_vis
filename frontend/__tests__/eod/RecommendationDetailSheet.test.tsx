import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RecommendationDetailSheet } from '@/components/eod/RecommendationDetailSheet';
import type { Recommendation, SignalStock } from '@/types/eod';

function rec(overrides: Partial<Recommendation> = {}): Recommendation {
  return {
    rank: 1, ticker: 'ABBV', company_name: 'AbbVie', signal_tag: 'P1', confidence: 'high', conf_ver: 1,
    composite_score: 1, thesis: '한 줄 논리',
    perspectives: { technical: '기술 서술', fundamental: '펀더 서술', news_context: '뉴스 서술' },
    risk: null, ...overrides,
  };
}
const stock = {
  symbol: 'ABBV', sector: 'Healthcare', market_cap: 443_244_148_968, dollar_volume: 803_061_805,
  technical: { rsi: 49.6, rsi_state: 'neutral', dist_52w_high_pct: 98.2, ma_state: 'above' },
} as unknown as SignalStock;

describe('RecommendationDetailSheet — 위험 섹션 (g 비대칭 해소)', () => {
  it('risk가 있으면 드로어에 위험 섹션을 그린다', () => {
    render(
      <RecommendationDetailSheet
        rec={rec({ risk: '밸류에이션 부담' })}
        stock={stock}
        axisCategories={['momentum']}
        onClose={() => {}}
      />,
    );
    expect(screen.getByRole('heading', { name: '위험' })).toBeInTheDocument();
    expect(screen.getByText('밸류에이션 부담')).toBeInTheDocument();
  });

  it('risk가 없으면 섹션 제목째 생략한다(정칙 ⑴ — "정보 없음" 금지)', () => {
    render(
      <RecommendationDetailSheet rec={rec()} stock={stock} axisCategories={['momentum']} onClose={() => {}} />,
    );
    expect(screen.queryByRole('heading', { name: '위험' })).not.toBeInTheDocument();
  });

  it('공백만 있는 risk도 생략한다', () => {
    render(
      <RecommendationDetailSheet
        rec={rec({ risk: '   ' })}
        stock={stock}
        axisCategories={['momentum']}
        onClose={() => {}}
      />,
    );
    expect(screen.queryByRole('heading', { name: '위험' })).not.toBeInTheDocument();
  });
});

describe('RecommendationDetailSheet — 3섹션', () => {
  it('한 줄 요약 · 세 관점 · 체급·기술을 그린다', () => {
    render(<RecommendationDetailSheet rec={rec()} stock={stock} axisCategories={['momentum', 'volume']} onClose={() => {}} />);
    expect(screen.getByRole('heading', { name: '한 줄 요약' })).toBeInTheDocument();
    expect(screen.getByText('한 줄 논리')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '세 관점' })).toBeInTheDocument();
    expect(screen.getByText('기술 서술')).toBeInTheDocument();
    expect(screen.getByText('펀더 서술')).toBeInTheDocument();
    expect(screen.getByText('뉴스 서술')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '체급·기술' })).toBeInTheDocument();
    expect(screen.getByText('Healthcare')).toBeInTheDocument();
    expect(screen.getByText('$443.2B')).toBeInTheDocument();
    expect(screen.getByText('$803M')).toBeInTheDocument();
    expect(screen.getByText('RSI 49.6 · 중립 · 52주 고점 −1.8% · 정배열')).toBeInTheDocument();
    expect(screen.getByText('2축')).toBeInTheDocument();
  });

  it('fundamental null → 드로어는 2관점(펀더 줄 생략)', () => {
    render(
      <RecommendationDetailSheet
        rec={rec({ perspectives: { technical: '기술 서술', fundamental: null, news_context: '뉴스 서술' } })}
        stock={stock}
        onClose={() => {}}
      />,
    );
    expect(screen.queryByText('펀더멘털', { selector: 'dt' })).toBeNull();
    expect(screen.getAllByRole('definition').filter((d) => d.textContent?.includes('서술'))).toHaveLength(2);
  });

  it('조인 실패(stock 없음) → 체급·기술 섹션만 제목째 보류', () => {
    render(<RecommendationDetailSheet rec={rec()} onClose={() => {}} />);
    expect(screen.queryByRole('heading', { name: '체급·기술' })).toBeNull();
    expect(screen.getByRole('heading', { name: '세 관점' })).toBeInTheDocument();
  });

  it('thesis·관점 전부 null → 두 섹션 제목째 생략', () => {
    render(
      <RecommendationDetailSheet
        rec={rec({ thesis: null, perspectives: { technical: null, fundamental: null, news_context: null } })}
        stock={stock}
        onClose={() => {}}
      />,
    );
    expect(screen.queryByRole('heading', { name: '한 줄 요약' })).toBeNull();
    expect(screen.queryByRole('heading', { name: '세 관점' })).toBeNull();
    expect(screen.getByRole('heading', { name: '체급·기술' })).toBeInTheDocument();
  });

  it('하단 커버리지 = 실제 보여준 축(스캐너 문구 "가치평가 · 퀄리티" 재사용 안 함)', () => {
    render(
      <RecommendationDetailSheet
        rec={rec({ perspectives: { technical: '기술 서술', fundamental: null, news_context: null } })}
        onClose={() => {}}
      />,
    );
    expect(screen.getByText(/이 화면 축:/).textContent).toContain('기술');
    expect(screen.getByText(/미커버:/).textContent).toBe('미커버: 펀더멘털 · 뉴스 · 관계(체인사이트)');
    expect(screen.queryByText(/가치평가 · 퀄리티/)).toBeNull();
  });

  it('ESC로 닫힌다(공용 셸)', () => {
    const onClose = vi.fn();
    render(<RecommendationDetailSheet rec={rec()} onClose={onClose} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
