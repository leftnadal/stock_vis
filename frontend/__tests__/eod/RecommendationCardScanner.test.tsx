import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RecommendationCard } from '@/components/eod/RecommendationCard';
import type { Recommendation } from '@/types/eod';

function rec(overrides: Partial<Recommendation> = {}): Recommendation {
  return {
    rank: 1,
    ticker: 'NVDA',
    company_name: 'NVIDIA',
    signal_tag: 'P1',
    confidence: 'high',
    conf_ver: 1,
    composite_score: 0.6,
    thesis: null,
    perspectives: { technical: null, fundamental: null, news_context: null },
    risk: null,
    ...overrides,
  };
}

describe('RecommendationCard — 스캐너 교차 배지 (STEP 4, 교집합 한정)', () => {
  it('scannerAxes≥2 → "스캐너 N축 포착" 배지 점등', () => {
    render(<RecommendationCard rec={rec()} scannerAxes={3} />);
    expect(screen.getByText('스캐너 3축 포착')).toBeInTheDocument();
  });

  it('scannerAxes<2(1축) → 배지 생략(합류 아님)', () => {
    render(<RecommendationCard rec={rec()} scannerAxes={1} />);
    expect(screen.queryByText(/스캐너 .*포착/)).toBeNull();
  });

  it('scannerAxes 미지정(기본 0=미로딩·교집합 밖) → 배지 생략(정칙 ⑴)', () => {
    render(<RecommendationCard rec={rec()} />);
    expect(screen.queryByText(/스캐너 .*포착/)).toBeNull();
  });

  it('배지 추가는 기존 표시(방향·signal_tag·신뢰)에 additive — 기존 요소 보존', () => {
    render(<RecommendationCard rec={rec()} scannerAxes={2} />);
    expect(screen.getByText('매수')).toBeInTheDocument();
    expect(screen.getByText('P1')).toBeInTheDocument();
    expect(screen.getByText('신뢰 높음')).toBeInTheDocument();
    expect(screen.getByText('스캐너 2축 포착')).toBeInTheDocument();
  });
});
