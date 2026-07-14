import { describe, it, expect, vi, afterEach } from 'vitest';

import {
  ImpressionQueue,
  IMPRESSION_FLUSH_INTERVAL_MS,
  IMPRESSION_MAX_RETRIES,
  IMPRESSION_BATCH_LIMIT,
} from '@/hooks/impressionTelemetry';

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

describe('ImpressionQueue', () => {
  it('5초 주기 배치 flush로 impression·click을 전송한다', async () => {
    vi.useFakeTimers();
    const send = vi.fn().mockResolvedValue(true);
    const q = new ImpressionQueue(send);
    q.enqueueImpression('dashboard_eod', 'AAPL:2026-07-14:V1');
    q.enqueueClick('news_chip', 'https://ex.com/a');
    expect(send).not.toHaveBeenCalled(); // flush 전
    await vi.advanceTimersByTimeAsync(IMPRESSION_FLUSH_INTERVAL_MS);
    expect(send).toHaveBeenCalledTimes(1);
    expect(send.mock.calls[0][0]).toHaveLength(2);
    expect(send.mock.calls[0][0][0]).toMatchObject({
      surface: 'dashboard_eod',
      object_ref: 'AAPL:2026-07-14:V1',
      event_type: 'impression',
    });
    q.destroy();
  });

  it('동일 (surface, object_ref) impression 재적재는 무시(페이지 수명 내 1회)', async () => {
    vi.useFakeTimers();
    const send = vi.fn().mockResolvedValue(true);
    const q = new ImpressionQueue(send);
    q.enqueueImpression('dashboard_eod', 'AAPL:2026-07-14:V1');
    q.enqueueImpression('dashboard_eod', 'AAPL:2026-07-14:V1'); // 중복 → 무시
    expect(q.pending).toBe(1);
    q.destroy();
  });

  it('pagehide 시 즉시 flush한다(이탈 유실 방지)', async () => {
    const send = vi.fn().mockResolvedValue(true);
    const q = new ImpressionQueue(send);
    q.enqueueImpression('dashboard_eod', 'A:1');
    window.dispatchEvent(new Event('pagehide'));
    await Promise.resolve();
    await Promise.resolve();
    expect(send).toHaveBeenCalledTimes(1);
    q.destroy();
  });

  it('전송 실패 시 큐 복원 후 재시도, 상한 초과 시 drop + warn', async () => {
    vi.useFakeTimers();
    const send = vi.fn().mockResolvedValue(false);
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const q = new ImpressionQueue(send);
    q.enqueueImpression('dashboard_eod', 'A:1');
    for (let i = 0; i < IMPRESSION_MAX_RETRIES + 1; i++) {
      await vi.advanceTimersByTimeAsync(IMPRESSION_FLUSH_INTERVAL_MS);
    }
    expect(send).toHaveBeenCalledTimes(IMPRESSION_MAX_RETRIES + 1); // 최초 + 재시도
    expect(warn).toHaveBeenCalled();
    expect(q.pending).toBe(0); // 상한 초과 → drop
    q.destroy();
  });

  it('배치 상한(100) 초과분은 다음 flush로 이월한다', async () => {
    vi.useFakeTimers();
    const send = vi.fn().mockResolvedValue(true);
    const q = new ImpressionQueue(send);
    for (let i = 0; i < IMPRESSION_BATCH_LIMIT + 5; i++) {
      q.enqueueImpression('dashboard_eod', `A:${i}`);
    }
    await vi.advanceTimersByTimeAsync(IMPRESSION_FLUSH_INTERVAL_MS);
    expect(send.mock.calls[0][0]).toHaveLength(IMPRESSION_BATCH_LIMIT);
    await vi.advanceTimersByTimeAsync(IMPRESSION_FLUSH_INTERVAL_MS);
    expect(send.mock.calls[1][0]).toHaveLength(5);
    q.destroy();
  });
});
