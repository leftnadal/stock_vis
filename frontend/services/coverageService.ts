// 커버리지 조회 API 클라이언트 (P2-COVERAGE-C1-FE)
// authAxios baseURL에 이미 /api/v1 포함 → 경로에 중복 금지 (common-bug #19)
import { authAxios } from '@/lib/api/authAxios'
import type { CoverageResponse } from '@/types/coverage'

/** 기본 조회 창(일). C1-API 기본값과 정합(상한 90은 백엔드 clamp). */
export const DEFAULT_COVERAGE_WINDOW_DAYS = 7

export const coverageService = {
  /** GET /api/v1/telemetry/coverage — 발급 대비 유기 노출 커버리지(요청 사용자 스코프). */
  getCoverage: async (
    windowDays: number = DEFAULT_COVERAGE_WINDOW_DAYS
  ): Promise<CoverageResponse> => {
    const { data } = await authAxios.get('/telemetry/coverage', {
      params: { window_days: windowDays },
    })
    return data as CoverageResponse
  },
}
