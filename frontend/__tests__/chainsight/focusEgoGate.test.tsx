/**
 * market-graph ?focus= 시드 게이트 해제 (⑳-E S2).
 *
 * 비시드 심볼도 focus 시 ego 초기화가 발생함을 페이지 effect 수준에서 검증.
 * 시드 심볼은 sector 브레드크럼 포함 초기화(기존 동작 보존).
 */

import { render } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const initFocusMock = vi.fn();
let focusParam = 'NVDA';
let seedList: Array<{ symbol: string; sector: string }> = [];

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(focusParam ? `focus=${focusParam}` : ''),
}));
vi.mock('@/hooks/useMarketView', () => ({
  useSeedData: () => ({
    data: { seeds: seedList, sector_summary: [{ sector: 'Technology' }] },
    isLoading: false,
  }),
}));
vi.mock('@/lib/stores/explorationStore', () => ({
  useExplorationStore: () => ({
    selectedSector: null,
    initializeFocusExploration: initFocusMock,
  }),
}));
// 자식 컴포넌트 sentinel — effect 배선만 검증
vi.mock('@/components/chainsight/SectorBar', () => ({ default: () => <div /> }));
vi.mock('@/components/chainsight/RelationFilterChips', () => ({ default: () => <div /> }));
vi.mock('@/components/chainsight/MarketGraphCanvas', () => ({ default: () => <div /> }));
vi.mock('@/components/chainsight/ExplorationTrail', () => ({ default: () => <div /> }));
vi.mock('@/components/chainsight/RelationCardPanel', () => ({ default: () => <div /> }));
vi.mock('@/components/chainsight/ChainStoryFeed', () => ({ default: () => <div /> }));

describe('⑳-E focus → ego 직행 (시드 게이트 해제)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('비시드 심볼 focus 시에도 ego 초기화가 발생한다 (sector=null)', async () => {
    focusParam = 'NVDA';
    seedList = [{ symbol: 'AMZN', sector: 'Consumer' }]; // NVDA 는 시드 아님
    const Page = (await import('@/app/chainsight/market-graph/page')).default;
    render(<Page />);
    expect(initFocusMock).toHaveBeenCalledWith(null, 'NVDA');
  });

  it('시드 심볼 focus 시 sector 브레드크럼 포함 초기화 (기존 동작 보존)', async () => {
    focusParam = 'AMZN';
    seedList = [{ symbol: 'AMZN', sector: 'Consumer Discretionary' }];
    const Page = (await import('@/app/chainsight/market-graph/page')).default;
    render(<Page />);
    expect(initFocusMock).toHaveBeenCalledWith('Consumer Discretionary', 'AMZN');
  });
});
