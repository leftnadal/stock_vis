import { useQuery } from '@tanstack/react-query'

import {
  coverageService,
  DEFAULT_COVERAGE_WINDOW_DAYS,
} from '@/services/coverageService'
import type { CoverageResponse } from '@/types/coverage'

const QUERY_KEYS = {
  coverage: (windowDays: number) => ['coverage', windowDays] as const,
}

export function useCoverage(windowDays: number = DEFAULT_COVERAGE_WINDOW_DAYS) {
  return useQuery<CoverageResponse>({
    queryKey: QUERY_KEYS.coverage(windowDays),
    queryFn: () => coverageService.getCoverage(windowDays),
    staleTime: 5 * 60 * 1000, // 5분 — 노출은 자주 안 바뀜(도그푸딩 지표)
    retry: 1,
  })
}
