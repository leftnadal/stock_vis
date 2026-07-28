// P2-COVERAGE-C1-FE — 커버리지 조회 API 타입
//
// 단일 출처 = C1-API 착지본(GET /api/v1/telemetry/coverage)의 실응답(2026-07-27 실측).
// FE에서 계약을 재정의하지 않는다 — 필드/의미는 백엔드가 진실의 소스.

/** 미노출 발급 항목 (정렬·상한은 API 응답 그대로 — FE 재정렬 금지). */
export interface CoverageUnexposedItem {
  object_ref: string
  ticker: string
  signal_date: string
  signal_tag: string
  days_since_issue: number
}

export interface CoverageResponse {
  window: {
    days: number
    from: string
    to: string
  }
  summary: {
    issued: number
    exposed: number
    exposure_rate: number
    unexposed_count: number
  }
  unexposed: CoverageUnexposedItem[]
  meta: {
    /** 유기 노출 집계에 포함된 표면 목록(단일 근거). coverage_detail은 제외됨. */
    surfaces_included: string[]
    generated_at: string
    /** in-window 발급에 귀속 안 된 노출 수(창밖 발급 관측 등). exposed에 미포함. */
    join_misses: number
  }
}
