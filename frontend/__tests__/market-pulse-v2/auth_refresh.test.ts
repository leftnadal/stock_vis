/**
 * A2 (MP1.5-FIX Step 3) — refreshAccessToken 공유 헬퍼 단위 테스트.
 * marketPulseV2 client / authAxios 단일 소스 검증. axios.post만 spy(create는 실제).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import axios from 'axios'

import { refreshAccessToken } from '@/lib/api/authAxios'

describe('refreshAccessToken (A2 단일 소스)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('refresh 토큰으로 access 갱신 + rotation(data.refresh) 저장', async () => {
    localStorage.setItem('refresh_token', 'r1')
    vi.spyOn(axios, 'post').mockResolvedValue({ data: { access: 'a2', refresh: 'r2' } } as never)

    const access = await refreshAccessToken()

    expect(access).toBe('a2')
    expect(localStorage.getItem('access_token')).toBe('a2')
    expect(localStorage.getItem('refresh_token')).toBe('r2') // rotation 반영
  })

  it('rotation 없으면 access만 갱신 (refresh 유지)', async () => {
    localStorage.setItem('refresh_token', 'r1')
    vi.spyOn(axios, 'post').mockResolvedValue({ data: { access: 'a2' } } as never)

    await refreshAccessToken()

    expect(localStorage.getItem('access_token')).toBe('a2')
    expect(localStorage.getItem('refresh_token')).toBe('r1')
  })

  it('refresh 토큰 없으면 throw (인터셉터가 reject → 로그인 유도)', async () => {
    await expect(refreshAccessToken()).rejects.toThrow('No refresh token')
  })
})
