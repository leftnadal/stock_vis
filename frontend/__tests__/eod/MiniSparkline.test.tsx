import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

import { MiniSparkline } from '@/components/eod/MiniSparkline';
import { DIRECTION_HEX_CHANGE } from '@/components/common/colorSemantics';

// stroke/fill prop 추가의 하위호환 회귀 가드 (기존 소비처=StockRow/SignalCard는 미전달).
describe('MiniSparkline stroke/fill prop', () => {
  it('기본(미전달): 상승 데이터 → 등락 방향색(rose) 유지 (회귀)', () => {
    const { container } = render(<MiniSparkline data={[1, 2, 3]} />);
    const line = container.querySelector('polyline');
    expect(line?.getAttribute('stroke')).toBe(DIRECTION_HEX_CHANGE.up);
  });

  it('기본(미전달): 하락 데이터 → 등락 방향색(sky) 유지 (회귀)', () => {
    const { container } = render(<MiniSparkline data={[3, 2, 1]} />);
    const line = container.querySelector('polyline');
    expect(line?.getAttribute('stroke')).toBe(DIRECTION_HEX_CHANGE.down);
  });

  it('stroke prop 지정 시 방향색 대신 사용', () => {
    const { container } = render(
      <MiniSparkline data={[1, 2, 3]} stroke="#ef4444" fill="rgba(239,68,68,0.14)" />,
    );
    const line = container.querySelector('polyline');
    expect(line?.getAttribute('stroke')).toBe('#ef4444');
    const area = container.querySelector('path');
    expect(area?.getAttribute('fill')).toBe('rgba(239,68,68,0.14)');
  });

  it('데이터 2개 미만이면 placeholder(빈 박스), svg 없음', () => {
    const { container } = render(<MiniSparkline data={[1]} />);
    expect(container.querySelector('svg')).toBeNull();
  });
});
