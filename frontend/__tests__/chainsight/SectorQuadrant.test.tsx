// QUAD-IMPL-1 Slice 2 — 섹터 사분면 순수함수 + 렌더 테스트
// (0-6 경로 자기정정: vitest include=__tests__/** 이므로 co-located 대신 여기 배치)
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  SectorQuadrant,
  heatMedian,
  assignZone,
  chartedSectors,
  unchartedSectors,
} from '@/components/charts/SectorQuadrant';
import type { QuadrantResponse, QuadrantSector } from '@/types/quadrant';

const mk = (over: Partial<QuadrantSector>): QuadrantSector => ({
  sector: 'X',
  heat: 50,
  heat_date: '2026-08-26',
  breadth_curr: 0.1,
  breadth_prev: 0.0,
  denom_curr: 20,
  denom_prev: 20,
  anchor_curr: '2026-08-21',
  anchor_prev: '2026-08-14',
  arrow_suppressed: false,
  ...over,
});

const resp = (sectors: QuadrantSector[], over: Partial<QuadrantResponse> = {}): QuadrantResponse => ({
  heat_date: '2026-08-26',
  anchor_curr: '2026-08-21',
  anchor_prev: '2026-08-14',
  arrow_suppressed: false,
  flat_ratio_curr: 0.07,
  flat_ratio_prev: 0.5,
  sectors,
  ...over,
});

describe('heatMedian (중앙값 경계)', () => {
  it('정렬 후 len//2 상단중앙 (백엔드 규약)', () => {
    const s = [42, 43, 48, 50, 50, 58].map((h) => mk({ heat: h }));
    expect(heatMedian(s)).toBe(50);
  });
  it('heat null 은 제외', () => {
    const s = [mk({ heat: 10 }), mk({ heat: null }), mk({ heat: 30 })];
    expect(heatMedian(s)).toBe(30); // [10,30] → index 1 = 30
  });
  it('전부 null → null', () => {
    expect(heatMedian([mk({ heat: null }), mk({ heat: null })])).toBeNull();
  });
});

describe('assignZone (구역 배정)', () => {
  const median = 50;
  it('② = 저Heat + 수요개선', () => {
    expect(assignZone(mk({ heat: 40, breadth_curr: 0.2 }), median)).toBe('II');
  });
  it('④ = 고Heat + 수요악화', () => {
    expect(assignZone(mk({ heat: 60, breadth_curr: -0.2 }), median)).toBe('IV');
  });
  it('경계(heat == median) → other', () => {
    expect(assignZone(mk({ heat: 50, breadth_curr: 0.2 }), median)).toBe('other');
  });
  it('저Heat + 수요악화 → other', () => {
    expect(assignZone(mk({ heat: 40, breadth_curr: -0.2 }), median)).toBe('other');
  });
  it('null heat/breadth/median → other', () => {
    expect(assignZone(mk({ heat: null, breadth_curr: 0.2 }), median)).toBe('other');
    expect(assignZone(mk({ heat: 40, breadth_curr: null }), median)).toBe('other');
    expect(assignZone(mk({ heat: 40, breadth_curr: 0.2 }), null)).toBe('other');
  });
});

describe('charted/uncharted (null 분리)', () => {
  it('heat null → uncharted, 나머지 charted', () => {
    const s = [mk({ sector: 'A', heat: 50 }), mk({ sector: 'B', heat: null }), mk({ sector: 'C', heat: 40, breadth_curr: null })];
    expect(chartedSectors(s).map((x) => x.sector)).toEqual(['A']);
    expect(unchartedSectors(s).map((x) => x.sector)).toEqual(['B']);
  });
});

describe('SectorQuadrant 렌더 (suppression / null)', () => {
  it('arrow_suppressed=true → 각주 노출', () => {
    render(<SectorQuadrant data={resp([mk({ heat: 50 })], { arrow_suppressed: true })} />);
    expect(screen.getByTestId('arrow-suppressed-note')).toBeInTheDocument();
  });
  it('arrow_suppressed=false → 각주 없음', () => {
    render(<SectorQuadrant data={resp([mk({ heat: 50 })], { arrow_suppressed: false })} />);
    expect(screen.queryByTestId('arrow-suppressed-note')).not.toBeInTheDocument();
  });
  it('heat null 섹터 → 하단 목록 노출', () => {
    render(<SectorQuadrant data={resp([mk({ sector: 'Utilities', heat: null }), mk({ sector: 'Tech', heat: 50 })])} />);
    const list = screen.getByTestId('uncharted-list');
    expect(list).toHaveTextContent('Utilities');
    expect(list).not.toHaveTextContent('Tech');
  });
});
