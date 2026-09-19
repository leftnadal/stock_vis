import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  SectorChipLine,
  buildSectorIndex,
  joinRecommendationSectors,
} from '@/components/eod/SectorChipLine';
import type { QuadrantResponse, QuadrantSector } from '@/types/quadrant';
import type { Recommendation, SignalCard } from '@/types/eod';

const useSectorQuadrant = vi.hoisted(() => vi.fn());
vi.mock('@/hooks/useSectorQuadrant', () => ({ useSectorQuadrant }));

function sector(name: string, heat: number | null, breadth: number | null): QuadrantSector {
  return { sector: name, heat, breadth_curr: breadth } as unknown as QuadrantSector;
}

/** heat 중앙값 = 50 → II = heat<50 & breadth>0 · IV = heat>50 & breadth<0 */
const RESPONSE: QuadrantResponse = {
  sectors: [
    sector('Energy', 10, 0.2),
    sector('Utilities', 20, 0.1),
    sector('Technology', 50, 0.05),
    sector('Healthcare', 90, -0.3),
  ],
} as unknown as QuadrantResponse;

function rec(ticker: string): Recommendation {
  return { ticker } as unknown as Recommendation;
}

function cardWith(stocks: { symbol: string; sector: string }[]): SignalCard {
  return { id: 'P1', preview_stocks: stocks } as unknown as SignalCard;
}

beforeEach(() => {
  useSectorQuadrant.mockReset();
});

describe('SectorChipLine — 정칙 ⑴ 조용한 생략', () => {
  it('데이터 미도달(비로그인·401)이면 아무것도 렌더하지 않는다', () => {
    useSectorQuadrant.mockReturnValue({ data: undefined });
    const { container } = render(<SectorChipLine />);
    expect(container).toBeEmptyDOMElement();
  });

  it('분류된 섹터가 없으면(전 섹터 other) 생략한다', () => {
    useSectorQuadrant.mockReturnValue({
      data: { sectors: [sector('A', null, null), sector('B', null, null)] },
    });
    const { container } = render(<SectorChipLine />);
    expect(container).toBeEmptyDOMElement();
  });

  it('heat는 있고 breadth_curr만 전건 null(DSS-BREADTH-MISSING 현 상태)이어도 생략한다', () => {
    useSectorQuadrant.mockReturnValue({
      data: { sectors: [sector('A', 10, null), sector('B', 50, null), sector('C', 90, null)] },
    });
    const { container } = render(<SectorChipLine />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('SectorChipLine — 한 줄 서술', () => {
  beforeEach(() => useSectorQuadrant.mockReturnValue({ data: RESPONSE }));

  it('구역 II/IV 섹터 수를 서술하고 시장 탭 링크를 준다', () => {
    render(<SectorChipLine />);
    expect(screen.getByText(/수요가 붙는 섹터 2곳/)).toBeInTheDocument();
    expect(screen.getByText(/관심 대비 수요가 빠지는 섹터 1곳/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /시장 탭에서 보기/ })).toHaveAttribute(
      'href',
      '?tab=market',
    );
  });

  it('onViewMarket이 있으면 버튼으로 탭을 바꾼다(쿼리 보존 경로)', () => {
    const onViewMarket = vi.fn();
    render(<SectorChipLine onViewMarket={onViewMarket} />);
    screen.getByRole('button', { name: /시장 탭에서 보기/ }).click();
    expect(onViewMarket).toHaveBeenCalledTimes(1);
  });

  it('조인이 전건 실패하면 추천 절만 생략한다 (J2 정칙)', () => {
    render(
      <SectorChipLine
        recommendations={[rec('ABBV'), rec('ABNB')]}
        cards={[cardWith([{ symbol: 'ZZZZ', sector: 'Energy' }])]}
      />,
    );
    expect(screen.getByText(/수요가 붙는 섹터 2곳/)).toBeInTheDocument();
    expect(screen.queryByText(/추천/)).not.toBeInTheDocument();
  });

  it('조인에 성공한 추천만 분모로 세어 서술한다', () => {
    render(
      <SectorChipLine
        recommendations={[rec('AAA'), rec('BBB'), rec('CCC')]}
        cards={[
          cardWith([
            { symbol: 'AAA', sector: 'Energy' },
            { symbol: 'BBB', sector: 'Healthcare' },
          ]),
        ]}
      />,
    );
    expect(screen.getByText(/추천 2종목 중 1곳이 수요가 붙는 섹터/)).toBeInTheDocument();
  });
});

describe('buildSectorIndex / joinRecommendationSectors', () => {
  it('preview_stocks를 symbol→sector 사전으로 만든다', () => {
    const index = buildSectorIndex([
      cardWith([{ symbol: 'AAA', sector: 'Energy' }, { symbol: 'BBB', sector: 'Tech' }]),
    ]);
    expect(index.get('AAA')).toBe('Energy');
    expect(index.size).toBe(2);
  });

  it('카드가 없으면 빈 사전 — resolved 0으로 조인 실패를 알린다', () => {
    const result = joinRecommendationSectors([rec('AAA')], buildSectorIndex(undefined), new Set());
    expect(result).toEqual({ resolved: 0, rising: 0 });
  });
});
