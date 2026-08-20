'use client'

import { useRouter } from 'next/navigation'

import { useCoverage } from '@/hooks/useCoverage'

/** 노출율(fraction 0~1) → 정수 % 문자열. */
function formatRate(rate: number): string {
  return `${Math.round(rate * 100)}%`
}

/**
 * 대시보드 상단 커버리지 스트립 (P2-COVERAGE-C1-FE, T1).
 *
 * 발급 N · 노출 M (율%) · 미노출 K건 — window_days=90 요청(D-C2-S2-FUNNEL-COV-A ⓐ-1:
 * "놓친 추천이 창 밖으로 사라지지 않게" = 적체 비제거 철학). 클릭 시 /dashboard/coverage 이동.
 * (전역 기본 상수는 7 유지 — /dashboard/coverage 상세의 7↔90 조인미스 대조를 보존.)
 * 스트립 자체는 impression 발신 없음(도그푸딩 지표 표시만).
 * - 로딩: 스켈레톤. 오류: 스트립 숨김(fail-quiet, 대시보드 본체 무영향).
 * - 발급 0: "이번 주 발급 없음" 문구.
 */
export function CoverageStrip() {
  const router = useRouter()
  const { data, isLoading, isError } = useCoverage(90)

  if (isLoading) {
    return (
      <div
        data-testid="coverage-strip-skeleton"
        className="mb-4 h-12 animate-pulse rounded-lg bg-gray-200"
      />
    )
  }

  // fail-quiet: 오류 시 스트립 자체를 숨긴다(본체 무영향).
  if (isError || !data) {
    return null
  }

  const { issued, exposed, exposure_rate, unexposed_count } = data.summary

  if (issued === 0) {
    return (
      <div
        data-testid="coverage-strip"
        className="mb-4 rounded-lg bg-white px-4 py-3 text-sm text-gray-500 shadow"
      >
        이번 주 발급 없음
      </div>
    )
  }

  return (
    <button
      type="button"
      data-testid="coverage-strip"
      onClick={() => router.push('/dashboard/coverage')}
      className="mb-4 flex w-full items-center justify-between rounded-lg bg-white px-4 py-3 text-left shadow transition hover:bg-gray-50"
    >
      <div className="flex items-center gap-4 text-sm">
        <span className="font-medium text-gray-900">이번 주 추천 커버리지</span>
        <span className="text-gray-600">
          발급 <strong className="text-gray-900">{issued}</strong> · 노출{' '}
          <strong className="text-gray-900">{exposed}</strong> (
          {formatRate(exposure_rate)}) · 미노출{' '}
          <strong className="text-gray-900">{unexposed_count}</strong>건
        </span>
      </div>
      <span className="text-sm font-medium text-blue-600">자세히 →</span>
    </button>
  )
}
