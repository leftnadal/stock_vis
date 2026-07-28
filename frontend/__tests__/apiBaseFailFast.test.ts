/**
 * FE-DEAD-8000-SWEEP — API base 단일 소스 fail-fast (#55).
 * env 미설정 시 죽은 포트 폴백 대신 즉시 throw하는지 검증.
 */
import { describe, it, expect, afterEach, vi } from 'vitest';

import { resolveApiBase } from '@/lib/api/config';

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('resolveApiBase (#55 fail-fast)', () => {
  it('NEXT_PUBLIC_API_URL 미설정 시 throw (죽은 포트 폴백 없음)', () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', '');
    expect(() => resolveApiBase()).toThrow(/NEXT_PUBLIC_API_URL/);
  });

  it('설정 시 후행 슬래시를 정규화한 절대 base 반환', () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://api.example.com/api/v1/');
    expect(resolveApiBase()).toBe('http://api.example.com/api/v1');
  });
});
