import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AttentionStandingBar from '@/components/chainsight/AttentionStandingBar';

// 채움 div(인라인 width style 보유)의 width% 추출. 트랙 div는 style 없음.
function fillWidth(container: HTMLElement): number {
  const fill = container.querySelector('div[style*="width"]') as HTMLElement;
  return parseFloat(fill.style.width);
}

describe('AttentionStandingBar (그룹 min-max 정규화)', () => {
  it('그룹 최고 점수는 100% 채움', () => {
    const { container } = render(<AttentionStandingBar score={85} groupMin={40} groupMax={85} />);
    expect(fillWidth(container)).toBeCloseTo(100, 1);
  });

  it('그룹 최저 점수는 FLOOR(10%) 채움 (흔적 보존)', () => {
    const { container } = render(<AttentionStandingBar score={40} groupMin={40} groupMax={85} />);
    expect(fillWidth(container)).toBeCloseTo(10, 1);
  });

  it('중간 점수는 FLOOR~100% 사이', () => {
    const { container } = render(<AttentionStandingBar score={62.5} groupMin={40} groupMax={85} />);
    const w = fillWidth(container);
    expect(w).toBeGreaterThan(10);
    expect(w).toBeLessThan(100);
  });

  it('점수에 단조 증가 (높은 점수 = 긴 바)', () => {
    const a = render(<AttentionStandingBar score={50} groupMin={40} groupMax={85} />);
    const b = render(<AttentionStandingBar score={70} groupMin={40} groupMax={85} />);
    expect(fillWidth(b.container)).toBeGreaterThan(fillWidth(a.container));
  });

  it('단일/동점 그룹(min==max)은 full (비교 대상 없음)', () => {
    const { container } = render(<AttentionStandingBar score={70} groupMin={70} groupMax={70} />);
    expect(fillWidth(container)).toBeCloseTo(100, 1);
  });

  it('범위 밖 점수도 [FLOOR,100]로 클램프', () => {
    const over = render(<AttentionStandingBar score={200} groupMin={40} groupMax={85} />);
    const under = render(<AttentionStandingBar score={0} groupMin={40} groupMax={85} />);
    expect(fillWidth(over.container)).toBeCloseTo(100, 1);
    expect(fillWidth(under.container)).toBeCloseTo(10, 1);
  });
});
