/**
 * INC-P16-1 Part A — TanStack Query 전역 retry 정책(429 무재시도).
 *
 * 배경: market-pulse-v2 페이지 마운트 시 동시 4엔드포인트(overview·regime/stress·
 * regime/analog·playbook) + retry 2 증폭이, 하드리프레시 반복 시 분당 요청을
 * throttle(market_pulse_user) 한도로 밀어올려 429 캐스케이드 → useOverview isError →
 * 전면 에러(page.tsx 게이팅)를 유발했다.
 *
 * 정책: 429(throttle)는 즉시 재시도 중단 — 429에 재시도하면 남은 예산을 더 태워
 * 캐스케이드를 악화시킨다(지수백오프해도 rate window 안에서 재소비). 그 외 실패
 * (500·네트워크 등)의 재시도 동작은 기존(retry: 2 = 최대 2회)을 그대로 보존한다.
 *
 * 참고: DRF ScopedRateThrottle은 429 응답에 Retry-After 헤더를 세팅한다. 향후
 * 지수백오프 대신 Retry-After를 존중하는 재시도로 고도화할 여지가 있으나, 이번
 * 핫픽스는 무재시도 단순형을 채택한다(구현·검증 최소·행위 예측 가능).
 */

/** 기존 전역 정책 값(retry: 2)을 함수형으로 옮기며 그대로 유지. */
export const MAX_QUERY_RETRY = 2

/** axios 에러(및 유사 형태)에서 HTTP 429 여부를 판별. 형태 방어적으로 추출. */
export function is429(error: unknown): boolean {
  const e = error as { response?: { status?: number }; status?: number } | null | undefined
  const status = e?.response?.status ?? e?.status
  return status === 429
}

/**
 * TanStack Query `retry` 함수. 429면 false(무재시도), 그 외는 기존 최대 2회.
 * failureCount는 누적 실패 횟수(1부터) — `failureCount < N`이 number형 `retry: N`과 동치.
 */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (is429(error)) return false
  return failureCount < MAX_QUERY_RETRY
}
