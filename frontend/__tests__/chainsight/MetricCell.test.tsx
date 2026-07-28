import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MetricCell from '@/components/chainsight/MetricCell';

describe('MetricCell', () => {
  it('null 값이면 "—"을 렌더하고 바가 없다', () => {
    const { container } = render(
      <MetricCell value={null} domain="center" domainMax={2} />
    );
    expect(screen.getByText('—')).toBeInTheDocument();
    // No colored bar element (only the empty container div)
    expect(container.querySelector('[class*="bg-rose"]')).toBeNull();
    expect(container.querySelector('[class*="bg-blue"]')).toBeNull();
    expect(container.querySelector('[class*="bg-sky"]')).toBeNull();
  });

  it('양수 값(center domain)은 값을 2자리로 표시하고 바가 존재한다', () => {
    const { container } = render(
      <MetricCell value={0.81} domain="center" domainMax={2} />
    );
    expect(screen.getByText('0.81')).toBeInTheDocument();
    // A bar element should exist inside the bar track
    const barTrack = container.querySelector('.relative');
    expect(barTrack).not.toBeNull();
    const bar = barTrack?.querySelector('[class*="bg-"]');
    expect(bar).not.toBeNull();
  });

  it('음수 값(center domain, signed)은 "-8.00"을 표시하고 바가 존재한다', () => {
    const { container } = render(
      <MetricCell value={-8} domain="center" domainMax={100} signed />
    );
    expect(screen.getByText('-8.00')).toBeInTheDocument();
    const barTrack = container.querySelector('.relative');
    const bar = barTrack?.querySelector('[class*="bg-"]');
    expect(bar).not.toBeNull();
  });

  it('0-baseline domain은 값을 2자리로 표시한다', () => {
    render(<MetricCell value={1.34} domain="baseline" domainMax={2} />);
    expect(screen.getByText('1.34')).toBeInTheDocument();
  });

  it('signed + 양수이면 바에 rose 클래스가 붙는다(한국축 긍정)', () => {
    const { container } = render(
      <MetricCell value={19} domain="center" domainMax={100} signed />
    );
    expect(screen.getByText('19.00')).toBeInTheDocument();
    const barTrack = container.querySelector('.relative');
    const bar = barTrack?.querySelector('[class*="bg-rose"]');
    expect(bar).not.toBeNull();
  });

  it('signed + 음수이면 바에 sky 클래스가 붙는다(한국축 부정)', () => {
    const { container } = render(
      <MetricCell value={-8} domain="center" domainMax={100} signed />
    );
    const barTrack = container.querySelector('.relative');
    const bar = barTrack?.querySelector('[class*="bg-sky"]');
    expect(bar).not.toBeNull();
  });

  it('도메인 경계 클램핑: value가 domainMax를 초과해도 바 너비가 100%를 넘지 않는다', () => {
    const { container } = render(
      <MetricCell value={300} domain="baseline" domainMax={100} />
    );
    expect(screen.getByText('300.00')).toBeInTheDocument();
    const barTrack = container.querySelector('.relative');
    const bar = barTrack?.querySelector('[style]') as HTMLElement | null;
    expect(bar).not.toBeNull();
    // width should be clamped at 100%
    expect(bar?.style.width).toBe('100%');
  });
});
