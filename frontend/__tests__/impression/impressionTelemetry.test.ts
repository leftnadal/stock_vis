import { describe, it, expect, vi, afterEach } from 'vitest';

import {
  ImpressionQueue,
  IMPRESSION_FLUSH_INTERVAL_MS,
  IMPRESSION_MAX_RETRIES,
  IMPRESSION_BATCH_LIMIT,
  defaultSend,
  type ImpressionEvent,
} from '@/hooks/impressionTelemetry';

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
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

  const sampleEvent = (): ImpressionEvent => ({
    surface: 'dashboard_eod',
    object_ref: 'AAPL:2026-07-14:V1',
    event_type: 'impression',
    session_id: 's',
  });

  it('defaultSend는 NEXT_PUBLIC_API_URL 절대 base로 전송한다(상대경로 금지)', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://api.example.com/api/v1');
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', fetchMock);

    const ok = await defaultSend([sampleEvent()]);

    expect(ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    // 절대 URL(호스트 포함) — 후행 슬래시 정규화 + /telemetry/impressions 부착
    expect(fetchMock.mock.calls[0][0]).toBe('http://api.example.com/api/v1/telemetry/impressions');
  });

  it('NEXT_PUBLIC_API_URL 미설정 시 전송을 skip한다(하드코딩 포트 폴백 없음)', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', '');
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', fetchMock);
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    const ok = await defaultSend([sampleEvent()]);

    expect(ok).toBe(true); // skip은 실패 아님 → 재시도 큐에 남기지 않음
    expect(fetchMock).not.toHaveBeenCalled();
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
