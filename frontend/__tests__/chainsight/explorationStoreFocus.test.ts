/**
 * explorationStore.initializeFocusExploration — ⑳-E 시드 게이트 해제 코어.
 *
 * 비시드 focus(sector=null)도 centerSymbol 을 세팅해 ego 모드로 진입시킨다.
 * (centerSymbol 이 MarketGraphCanvas 의 useEgo 발화 조건.)
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useExplorationStore } from '@/lib/stores/explorationStore';

describe('initializeFocusExploration (⑳-E)', () => {
  beforeEach(() => {
    useExplorationStore.getState().reset();
  });

  it('비시드(sector=null): centerSymbol 세팅 + trail 은 종목만(섹터 브레드크럼 없음)', () => {
    useExplorationStore.getState().initializeFocusExploration(null, 'NVDA');
    const s = useExplorationStore.getState();
    expect(s.centerSymbol).toBe('NVDA'); // ← ego 모드 발화 조건
    expect(s.selectedSector).toBeNull();
    expect(s.trail).toEqual([{ symbol: 'NVDA', type: 'stock', depth: 0 }]);
  });

  it('시드(sector 있음): 기존 동작 보존 — 섹터 브레드크럼 + 종목 2단 trail', () => {
    useExplorationStore.getState().initializeFocusExploration('Technology', 'AAPL');
    const s = useExplorationStore.getState();
    expect(s.centerSymbol).toBe('AAPL');
    expect(s.selectedSector).toBe('Technology');
    expect(s.trail).toEqual([
      { symbol: 'Technology', type: 'sector', depth: 0 },
      { symbol: 'AAPL', type: 'stock', depth: 1 },
    ]);
  });
});
