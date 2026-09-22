import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import {
  applyScannerFilters,
  buildOptionCounts,
  countByOption,
  DEFAULT_SCANNER_FILTERS,
  MKTCAP_OPTS,
  DVOL_OPTS,
  type ScannerFilters,
} from '@/components/eod/scannerFilters';
import { ScannerFilterBar } from '@/components/eod/ScannerFilterBar';
import type { SignalStock } from '@/types/eod';

function stock(
  symbol: string,
  market_cap: number,
  dollar_volume: number,
  sector = 'Technology',
): SignalStock {
  return { symbol, market_cap, dollar_volume, sector, news_context: null } as unknown as SignalStock;
}

/** 실측(2026-09-20 카드 payload)을 닮은 모집단: 거래대금은 전부 $50M을 크게 넘는다. */
const STOCKS: SignalStock[] = [
  stock('AAA', 80_000_000_000, 900_000_000),
  stock('BBB', 60_000_000_000, 800_000_000, 'Healthcare'),
  stock('CCC', 20_000_000_000, 700_000_000),
  stock('DDD', 5_000_000_000, 600_000_000, 'Energy'),
];

const F = DEFAULT_SCANNER_FILTERS;

describe('countByOption — 세는 규칙 == 거르는 규칙', () => {
  it('다른 축의 현재 선택을 유지한 채 그 축 하나만 바꿔 센다', () => {
    const filters: ScannerFilters = { ...F, sector: 'Technology' };
    // Technology 3건(AAA·CCC·DDD) 중 시총 $50B+ 는 AAA 하나.
    expect(countByOption(STOCKS, filters, undefined, 'marketCapMin', 50_000_000_000)).toBe(1);
    // 섹터 선택을 무시하고 전체에서 셌다면 2(AAA·BBB)가 나온다 — 그러면 실패.
    expect(countByOption(STOCKS, F, undefined, 'marketCapMin', 50_000_000_000)).toBe(2);
  });

  it('같은 입력에서 applyScannerFilters 길이와 정확히 일치한다', () => {
    const filters: ScannerFilters = { ...F, sector: 'Technology' };
    for (const o of [...MKTCAP_OPTS, ...DVOL_OPTS]) {
      const axis = MKTCAP_OPTS.includes(o) ? 'marketCapMin' : 'dollarVolumeMin';
      const counted = countByOption(STOCKS, filters, undefined, axis, o.value);
      const filtered = applyScannerFilters(STOCKS, { ...filters, [axis]: o.value }, undefined).length;
      expect(counted).toBe(filtered);
    }
  });
});

describe('ScannerFilterBar — 살아 있는 필터 표시 규칙', () => {
  const sectors = ['Energy', 'Healthcare', 'Technology'];
  const renderBar = (filters: ScannerFilters, stocks = STOCKS) =>
    render(
      <ScannerFilterBar
        filters={filters}
        onFiltersChange={() => {}}
        sort="confluence"
        onSortChange={() => {}}
        sectors={sectors}
        resultCount={applyScannerFilters(stocks, filters, undefined).length}
        totalCount={stocks.length}
        optionCounts={buildOptionCounts(stocks, filters, undefined, sectors)}
      />,
    );

  it('아무것도 거르지 못하는 옵션은 렌더하지 않는다', () => {
    renderBar(F);
    // 거래대금 최소가 $600M → $1M+·$10M+·$50M+ 전부 4건 = 아무것도 못 거름.
    expect(screen.queryByRole('option', { name: /\$1M\+/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /\$50M\+/ })).not.toBeInTheDocument();
    // 시총은 실제로 거르므로 남는다.
    expect(screen.getByRole('option', { name: /\$50B\+ \(2\)/ })).toBeInTheDocument();
  });

  it('축의 옵션이 전부 죽으면 그 select를 통째로 렌더하지 않는다', () => {
    renderBar(F);
    expect(screen.queryByLabelText('거래대금 하한')).not.toBeInTheDocument();
    expect(screen.getByLabelText('시가총액 하한')).toBeInTheDocument();
  });

  it('현재 선택된 옵션은 숨김 조건에 걸려도 렌더된다 (select value ↔ DOM 정합)', () => {
    // $1M+ 를 선택한 상태: 아무것도 못 거르지만 숨기면 브라우저가 첫 옵션을 보여주고
    // 상태는 그대로 남아 화면과 상태가 갈라진다.
    const filters: ScannerFilters = { ...F, dollarVolumeMin: 1_000_000 };
    renderBar(filters);
    const select = screen.getByLabelText('거래대금 하한') as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /\$1M\+/ })).toBeInTheDocument();
    expect(select.value).toBe('1000000');
  });

  it('결과가 0인 옵션은 숨기지 않고 disabled + (0)으로 표시한다', () => {
    const tiny = [stock('ZZZ', 1_000_000_000, 700_000_000)];
    render(
      <ScannerFilterBar
        filters={F}
        onFiltersChange={() => {}}
        sort="confluence"
        onSortChange={() => {}}
        sectors={['Technology']}
        resultCount={1}
        totalCount={1}
        optionCounts={buildOptionCounts(tiny, F, undefined, ['Technology'])}
      />,
    );
    const opt = screen.getByRole('option', { name: /\$50B\+ \(0\)/ }) as HTMLOptionElement;
    expect(opt).toBeInTheDocument();
    expect(opt.disabled).toBe(true);
  });

  it('전체(해제) 옵션은 결과가 같아도 항상 남는다', () => {
    renderBar(F);
    expect(screen.getByRole('option', { name: /시총 전체/ })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /섹터 전체/ })).toBeInTheDocument();
  });

  it('optionCounts 미지정이면 종전대로 전량 렌더하고 개수를 붙이지 않는다', () => {
    render(
      <ScannerFilterBar
        filters={F}
        onFiltersChange={() => {}}
        sort="confluence"
        onSortChange={() => {}}
        sectors={sectors}
        resultCount={4}
        totalCount={4}
      />,
    );
    expect(screen.getByLabelText('거래대금 하한')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '$1M+' })).toBeInTheDocument();
  });
});
