import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { MacroStrip } from '@/components/strip/MacroStrip';
import { useCreditSignals } from '@/hooks/useCreditSignals';
import type { CreditSignal } from '@/services/creditSignalsService';

vi.mock('@/hooks/useCreditSignals', () => ({ useCreditSignals: vi.fn() }));

const mockUse = vi.mocked(useCreditSignals);

function sig(overrides: Partial<CreditSignal>): CreditSignal {
  return {
    key: 'HY_OAS',
    name: 'US HY OAS',
    value: 2.7,
    z: -1.08,
    grade: 'gray',
    spark: [
      { date: '2026-07-01', value: 2.6 },
      { date: '2026-07-02', value: 2.7 },
    ],
    ...overrides,
  };
}

function mockResult(partial: unknown) {
  mockUse.mockReturnValue(partial as ReturnType<typeof useCreditSignals>);
}

describe('MacroStrip', () => {
  beforeEach(() => vi.clearAllMocks());

  it('실패 격리: isError면 null 렌더', () => {
    mockResult({ isError: true, data: undefined });
    const { container } = render(<MacroStrip />);
    expect(container.firstChild).toBeNull();
  });

  it('빈 응답(signals 0)이면 비표시', () => {
    mockResult({ isError: false, data: { as_of: '2026-07-08', signals: [] } });
    const { container } = render(<MacroStrip />);
    expect(container.firstChild).toBeNull();
  });

  it('데이터 미도착이면 비표시', () => {
    mockResult({ isError: false, data: undefined });
    const { container } = render(<MacroStrip />);
    expect(container.firstChild).toBeNull();
  });

  it('6종 칩을 렌더한다(실데이터 분포 gray 5 + yellow 1)', () => {
    const signals = [
      sig({ key: 'HY_OAS', name: 'US HY OAS', grade: 'gray', value: 2.7, z: -1.08 }),
      sig({ key: 'IG_OAS', name: 'US IG OAS', grade: 'gray', value: 0.76, z: -1.01 }),
      sig({ key: 'BBB_OAS', name: 'BBB OAS', grade: 'gray', value: 0.94, z: -1.2 }),
      sig({ key: 'CCC_OAS', name: 'CCC- OAS', grade: 'yellow', value: 9.75, z: 1.11 }),
      sig({ key: 'CURVE_10Y2Y', name: '10Y-2Y', grade: 'gray', value: 0.38, z: 0.28 }),
      sig({ key: 'VIX', name: 'VIX Close', grade: 'gray', value: 16.9, z: 0.15 }),
    ];
    mockResult({ isError: false, data: { as_of: '2026-07-08', signals } });
    render(<MacroStrip />);
    const chips = screen.getAllByTestId('grade-chip');
    expect(chips).toHaveLength(6);
    expect(chips.filter((c) => c.getAttribute('data-grade') === 'gray')).toHaveLength(5);
    expect(chips.filter((c) => c.getAttribute('data-grade') === 'yellow')).toHaveLength(1);
    // 값·z 병기(색 단독 인코딩 금지)
    expect(screen.getByText('9.75')).toBeInTheDocument();
    expect(screen.getByText('z +1.11')).toBeInTheDocument();
    expect(screen.getByText('z -1.08')).toBeInTheDocument();
  });

  it('z=null(콜드스타트)이면 "z —" 표기', () => {
    mockResult({
      isError: false,
      data: { as_of: '2026-07-08', signals: [sig({ z: null, spark: [] })] },
    });
    render(<MacroStrip />);
    expect(screen.getByText('z —')).toBeInTheDocument();
  });

  it('헤드라인: CCC 단독 yellow → HY 내부 분화 (규칙 자동 문장)', () => {
    const signals = [
      sig({ key: 'HY_OAS', name: 'US HY OAS', grade: 'gray' }),
      sig({ key: 'CCC_OAS', name: 'CCC- OAS', grade: 'yellow', value: 9.75, z: 1.11 }),
      sig({ key: 'VIX', name: 'VIX Close', grade: 'gray' }),
    ];
    mockResult({ isError: false, data: { as_of: '2026-07-08', signals } });
    render(<MacroStrip />);
    expect(screen.getByTestId('macro-headline')).toHaveTextContent(
      'HY 내부 분화 — CCC 스프레드 단독 상승',
    );
  });

  it('헤드라인: 전부 gray → 안정 문장', () => {
    const signals = [
      sig({ key: 'HY_OAS', name: 'US HY OAS', grade: 'gray' }),
      sig({ key: 'VIX', name: 'VIX Close', grade: 'gray' }),
    ];
    mockResult({ isError: false, data: { as_of: '2026-07-08', signals } });
    render(<MacroStrip />);
    expect(screen.getByTestId('macro-headline')).toHaveTextContent(
      '크레딧 전반 안정 — 특이 신호 없음',
    );
  });

  it('리드아웃 기본 = 최고 심각도 신호(정의·상태·밴드)', () => {
    const signals = [
      sig({ key: 'HY_OAS', name: 'US HY OAS', grade: 'gray' }),
      sig({ key: 'CCC_OAS', name: 'CCC- OAS', grade: 'yellow', value: 9.75, z: 1.11 }),
    ];
    mockResult({ isError: false, data: { as_of: '2026-07-08', signals } });
    render(<MacroStrip />);
    const readout = screen.getByTestId('macro-readout');
    // 기본 = 최고 심각도(CCC yellow)
    expect(readout.textContent).toContain('CCC- OAS');
    expect(readout.textContent).toContain('최저신용');
    // 신호별 도출 밴드 (CCC=비-HY → red 없음, orange 무상한, signed z)
    expect(readout.textContent).toContain('밴드 gray z<1(음수 포함) · yellow 1≤z<2 · orange z≥2');
    expect(readout.textContent).not.toContain('red');
  });

  it('칩 hover 시 리드아웃이 해당 신호로 갱신', () => {
    const signals = [
      sig({ key: 'HY_OAS', name: 'US HY OAS', grade: 'gray' }),
      sig({ key: 'CCC_OAS', name: 'CCC- OAS', grade: 'yellow', value: 9.75, z: 1.11 }),
    ];
    mockResult({ isError: false, data: { as_of: '2026-07-08', signals } });
    render(<MacroStrip />);
    // HY 칩 hover → 리드아웃이 HY 정의로
    const hyChip = screen.getAllByTestId('grade-chip').find((c) =>
      c.textContent?.includes('US HY OAS'),
    )!;
    fireEvent.mouseEnter(hyChip);
    expect(screen.getByTestId('macro-readout').textContent).toContain('하이일드');
  });
});
