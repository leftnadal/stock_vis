/**
 * INC-P16-1 Part A — 전역 retry 정책 단위 테스트.
 * 429 → 무재시도 / 그 외(500·네트워크) → 기존 최대 2회 보존을 고정.
 */
import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import { is429, shouldRetryQuery, MAX_QUERY_RETRY } from '@/providers/queryRetry'

describe('is429', () => {
  it('axios 형태(error.response.status=429) 감지', () => {
    expect(is429({ response: { status: 429 } })).toBe(true)
  })
  it('평평한 형태(error.status=429)도 감지', () => {
    expect(is429({ status: 429 })).toBe(true)
  })
  it('429 아님 / null / undefined는 false', () => {
    expect(is429({ response: { status: 500 } })).toBe(false)
    expect(is429(new Error('network'))).toBe(false)
    expect(is429(null)).toBe(false)
    expect(is429(undefined)).toBe(false)
  })
})

describe('shouldRetryQuery', () => {
  it('429는 첫 실패부터 즉시 무재시도', () => {
    const err429 = { response: { status: 429 } }
    expect(shouldRetryQuery(0, err429)).toBe(false)
    expect(shouldRetryQuery(1, err429)).toBe(false)
  })

  it('500은 기존 동작 보존 — failureCount < 2 동안 재시도', () => {
    const err500 = { response: { status: 500 } }
    expect(shouldRetryQuery(0, err500)).toBe(true) // 1차 재시도
    expect(shouldRetryQuery(1, err500)).toBe(true) // 2차 재시도
    expect(shouldRetryQuery(2, err500)).toBe(false) // 2회 소진 → 중단
  })

  it('네트워크 에러(status 없음)도 기존 재시도 정책 유지', () => {
    const netErr = new Error('Network Error')
    expect(shouldRetryQuery(0, netErr)).toBe(true)
    expect(shouldRetryQuery(MAX_QUERY_RETRY, netErr)).toBe(false)
  })
})

// 재현 검증(INC-P16-1): 실제 react-query 실행 루프에 predicate를 물려
// 429 캐스케이드 부재(재시도 0)와 그 외 실패의 기존 재시도(3회 호출) 보존을 입증.
describe('QueryClient 통합 — 429 무재시도로 캐스케이드 차단', () => {
  const makeClient = () =>
    new QueryClient({
      defaultOptions: { queries: { retry: shouldRetryQuery, retryDelay: 0 } },
    })

  it('429 쿼리는 재시도 없이 queryFn 1회만 호출(예산 재소비 없음)', async () => {
    const qc = makeClient()
    const fn = vi.fn().mockRejectedValue({ response: { status: 429 } })
    await expect(
      qc.fetchQuery({ queryKey: ['inc-p16', '429'], queryFn: fn }),
    ).rejects.toBeTruthy()
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('500 쿼리는 기존대로 3회(1+재시도2) 호출 — 타 실패 재시도 보존', async () => {
    const qc = makeClient()
    const fn = vi.fn().mockRejectedValue({ response: { status: 500 } })
    await expect(
      qc.fetchQuery({ queryKey: ['inc-p16', '500'], queryFn: fn }),
    ).rejects.toBeTruthy()
    expect(fn).toHaveBeenCalledTimes(3)
  })
})
