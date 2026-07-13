import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

import { GradeChip } from '@/components/strip/GradeChip';
import { GRADE_DOT_HEX } from '@/components/common/colorSemantics';

describe('GradeChip', () => {
  it('grade별 data-grade + 도트 색을 grade 토큰에서 소비', () => {
    render(<GradeChip grade="yellow" label="CCC- OAS" value="9.75" sub="z +1.11" />);
    const chip = screen.getByTestId('grade-chip');
    expect(chip.getAttribute('data-grade')).toBe('yellow');
    const dot = screen.getByTestId('grade-dot');
    // 인라인 style backgroundColor = GRADE_DOT_HEX.yellow (hex→rgb 변환되어도 색 일치)
    expect(dot).toHaveStyle({ backgroundColor: GRADE_DOT_HEX.yellow });
  });

  it('라벨·값·보조(z)를 병기 렌더', () => {
    render(<GradeChip grade="gray" label="US HY OAS" value="2.70" sub="z -1.08" />);
    expect(screen.getByText('US HY OAS')).toBeInTheDocument();
    expect(screen.getByText('2.70')).toBeInTheDocument();
    expect(screen.getByText('z -1.08')).toBeInTheDocument();
  });

  it('spark 2개 이상이면 스파크라인(svg) 렌더', () => {
    const { container } = render(
      <GradeChip grade="gray" label="X" value="1.0" spark={[1, 2, 3]} />,
    );
    expect(container.querySelector('svg')).toBeTruthy();
  });

  it('spark 2개 미만이면 스파크라인 생략(칩은 값만)', () => {
    const { container } = render(
      <GradeChip grade="gray" label="X" value="1.0" spark={[]} />,
    );
    expect(container.querySelector('svg')).toBeNull();
    expect(screen.getByText('1.0')).toBeInTheDocument();
  });

  it('spark 미전달이면 스파크라인 생략', () => {
    const { container } = render(<GradeChip grade="red" label="X" value="1.0" />);
    expect(container.querySelector('svg')).toBeNull();
  });

  it('info 미전달이면 툴팁 없음 + focusable 아님 (하위호환)', () => {
    render(<GradeChip grade="gray" label="X" value="1.0" />);
    expect(screen.queryByTestId('grade-tooltip')).toBeNull();
    expect(screen.getByTestId('grade-chip').getAttribute('tabindex')).toBeNull();
  });

  it('info 전달 시 툴팁(정의·상태·밴드) + focusable', () => {
    render(
      <GradeChip
        grade="yellow"
        label="CCC- OAS"
        value="9.75"
        info={{ def: '최저신용 회사채 가산금리.', state: '현재 9.75 · z +1.11 · 최근 30일 상승', band: 'gray |z|<1 · yellow 1–2 · orange 2–3 · red ≥3' }}
      />,
    );
    const tip = screen.getByTestId('grade-tooltip');
    expect(tip).toBeInTheDocument();
    expect(tip.textContent).toContain('최저신용');
    expect(tip.textContent).toContain('현재 9.75');
    expect(tip.textContent).toContain('red ≥3');
    expect(screen.getByTestId('grade-chip').getAttribute('tabindex')).toBe('0');
  });
});
