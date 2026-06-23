import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AttentionStandingBar from '@/components/chainsight/AttentionStandingBar';

// 채움 div(인라인 width style 보유)의 width% 추출. 트랙 div는 style 없음.
function fillWidth(container: HTMLElement): number {
  const fill = container.querySelector('div[style*="width"]') as HTMLElement;
  return parseFloat(fill.style.width);
}

describe('AttentionStandingBar (전역 0~100 절대 도메인)', () => {
  // (a) 경계 + 단조
  it('score=100 → 100% 채움', () => {
    const { container } = render(<AttentionStandingBar score={100} />);
    expect(fillWidth(container)).toBeCloseTo(100, 1);
  });

  it('score=0 → FLOOR(10%) 채움 (0점 가시성)', () => {
    const { container } = render(<AttentionStandingBar score={0} />);
    expect(fillWidth(container)).toBeCloseTo(10, 1);
  });

  it('score에 단조 증가 (높은 점수 = 긴 바)', () => {
    const a = render(<AttentionStandingBar score={50} />);
    const b = render(<AttentionStandingBar score={70} />);
    expect(fillWidth(b.container)).toBeGreaterThan(fillWidth(a.container));
  });

  it('중간 점수(50)는 FLOOR~100% 사이 (= 55%)', () => {
    const { container } = render(<AttentionStandingBar score={50} />);
    expect(fillWidth(container)).toBeCloseTo(55, 1);
  });

  // (b) 촘촘한 두 점수 — 과장 사라짐: 거의 같은 바 폭
  it('촘촘한 두 점수(62.0·64.1)는 바 폭이 거의 같다 (소규모 그룹 과장 0)', () => {
    const a = render(<AttentionStandingBar score={62.0} />);
    const b = render(<AttentionStandingBar score={64.1} />);
    const wa = fillWidth(a.container);
    const wb = fillWidth(b.container);
    // 2.1점 차 → 0.9·2.1 = 1.89%p 차이뿐(과거엔 10%↔100%로 과장됨)
    expect(Math.abs(wb - wa)).toBeLessThan(3);
  });

  // (c) 그룹 무관 — 같은 점수 = 같은 바 폭 (그룹 간 비교 가능)
  it('그룹과 무관하게 같은 점수는 같은 바 폭 (그룹 간 비교 가능)', () => {
    // 과거엔 groupMin/Max 주입에 따라 같은 점수도 다른 폭이었음 → 이제 props는 score뿐
    const a = render(<AttentionStandingBar score={75} />);
    const b = render(<AttentionStandingBar score={75} />);
    expect(fillWidth(a.container)).toBeCloseTo(fillWidth(b.container), 5);
  });

  it('범위 밖 점수도 [FLOOR,100]로 클램프', () => {
    const over = render(<AttentionStandingBar score={200} />);
    const under = render(<AttentionStandingBar score={-50} />);
    expect(fillWidth(over.container)).toBeCloseTo(100, 1);
    expect(fillWidth(under.container)).toBeCloseTo(10, 1);
  });
});
