import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, cleanup, render } from '@testing-library/react';

import { useImpressionTracker } from '@/hooks/useImpressionTracker';
import {
  impressionQueue,
  IMPRESSION_DWELL_MS,
} from '@/hooks/impressionTelemetry';

// IntersectionObserver 목 — 관측 콜백을 잡아 수동 트리거.
let ioInstances: MockIO[] = [];
class MockIO {
  cb: IntersectionObserverCallback;
  constructor(cb: IntersectionObserverCallback) {
    this.cb = cb;
    ioInstances.push(this);
  }
  observe() {}
  unobserve() {}
  disconnect() {}
  trigger(ratio: number) {
    this.cb(
      [{ isIntersecting: ratio > 0, intersectionRatio: ratio } as IntersectionObserverEntry],
      this as unknown as IntersectionObserver,
    );
  }
}

function Probe({ surface = 'dashboard_eod', objectRef = 'A:1' }: { surface?: string; objectRef?: string }) {
  const { ref, onClick } = useImpressionTracker<HTMLDivElement>(surface, objectRef);
  return <div ref={ref} data-testid="probe" onClick={onClick} />;
}

let enqueueSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  ioInstances = [];
  vi.useFakeTimers();
  vi.stubGlobal('IntersectionObserver', MockIO as unknown as typeof IntersectionObserver);
  enqueueSpy = vi.spyOn(impressionQueue, 'enqueueImpression').mockImplementation(() => {});
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('useImpressionTracker', () => {
  it('뷰포트 50% 이상 · 1초 연속 노출 시 impression 1건 적재', () => {
    render(<Probe surface="dashboard_eod" objectRef="AAPL:2026-07-14:V1" />);
    act(() => ioInstances[0].trigger(0.6));
    expect(enqueueSpy).not.toHaveBeenCalled(); // dwell 전
    act(() => vi.advanceTimersByTime(IMPRESSION_DWELL_MS));
    expect(enqueueSpy).toHaveBeenCalledTimes(1);
    expect(enqueueSpy).toHaveBeenCalledWith('dashboard_eod', 'AAPL:2026-07-14:V1');
  });

  it('가시성 미달(0.4) 시 미적재', () => {
    render(<Probe />);
    act(() => ioInstances[0].trigger(0.4));
    act(() => vi.advanceTimersByTime(IMPRESSION_DWELL_MS * 2));
    expect(enqueueSpy).not.toHaveBeenCalled();
  });

  it('1초 미만(0.8초) 노출 후 벗어나면 미적재', () => {
    render(<Probe />);
    act(() => ioInstances[0].trigger(0.6)); // 진입 → dwell 시작
    act(() => vi.advanceTimersByTime(800)); // 0.8초
    act(() => ioInstances[0].trigger(0)); // 벗어남 → dwell 취소
    act(() => vi.advanceTimersByTime(IMPRESSION_DWELL_MS));
    expect(enqueueSpy).not.toHaveBeenCalled();
  });

  it('click 시 enqueueClick 호출', () => {
    const clickSpy = vi.spyOn(impressionQueue, 'enqueueClick').mockImplementation(() => {});
    const { getByTestId } = render(<Probe surface="news_chip" objectRef="https://ex.com/a" />);
    act(() => getByTestId('probe').click());
    expect(clickSpy).toHaveBeenCalledWith('news_chip', 'https://ex.com/a');
  });
});
