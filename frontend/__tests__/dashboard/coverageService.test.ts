// coverageService 데이터 레이어 검증 (P2-COVERAGE-C1-FE)
// base config(authAxios) 경유 + 계약 필드 확인.
import { beforeEach, describe, expect, it, vi } from 'vitest'

const get = vi.fn()

vi.mock('@/lib/api/authAxios', () => ({
  authAxios: { get: (...a: unknown[]) => get(...a) },
}))

import { coverageService } from '@/services/coverageService'

const SAMPLE = {
  window: { days: 7, from: '2026-07-20', to: '2026-07-27' },
  summary: { issued: 50, exposed: 4, exposure_rate: 0.08, unexposed_count: 46 },
  unexposed: [
    {
      object_ref: 'ACGL:2026-07-24:P5',
      ticker: 'ACGL',
      signal_date: '2026-07-24',
      signal_tag: 'P5',
      days_since_issue: 3,
    },
  ],
  meta: {
    surfaces_included: ['dashboard_eod'],
    generated_at: '2026-07-27T00:00:00Z',
    join_misses: 8,
  },
}

beforeEach(() => get.mockReset())

describe('coverageService', () => {
  it('getCoverage는 base config(authAxios) 경유 /telemetry/coverage + 기본 window_days=7 로 호출', async () => {
    get.mockResolvedValue({ data: SAMPLE })
    const res = await coverageService.getCoverage()
    expect(get).toHaveBeenCalledWith('/telemetry/coverage', {
      params: { window_days: 7 },
    })
    // 계약 필드
    expect(res.summary.issued).toBe(50)
    expect(res.summary.exposure_rate).toBe(0.08)
    expect(res.meta.surfaces_included).toEqual(['dashboard_eod'])
    expect(res.meta.join_misses).toBe(8)
  })

  it('window_days 인자를 파라미터로 전달', async () => {
    get.mockResolvedValue({ data: SAMPLE })
    await coverageService.getCoverage(90)
    expect(get).toHaveBeenCalledWith('/telemetry/coverage', {
      params: { window_days: 90 },
    })
  })
})
