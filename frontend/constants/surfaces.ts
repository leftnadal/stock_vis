/**
 * SURFACES — impression 텔레메트리 surface 값 단일 출처 (D-C2-S1-CONST-UNIFY ⓒ-3).
 *
 * 백엔드 `ImpressionLog.SURFACE_CHOICES` 미러 — 값 스냅샷 동결(2026-08-10 실측,
 * `packages/shared/stocks/models.py:1263-1266`). 값 변경 시 백엔드와 동반 갱신 +
 * 가드 테스트(`__tests__/surfaces.guard.test.ts`)의 스냅샷 동반 갱신 필수.
 *
 * 위치 = 공용 frontend 인프라(shared 트랙 `constants/`) — dashboard·strip·eod 등
 * 다트랙이 소비하므로 특정 feature 구획에 두면 의존 역전(BATCH-25 백-어노 근거).
 */
export const SURFACES = {
  DASHBOARD_EOD: 'dashboard_eod',
  CHAIN_SIGHT: 'chain_sight',
  NEWS_CHIP: 'news_chip',
  COVERAGE_DETAIL: 'coverage_detail',
} as const

export type Surface = (typeof SURFACES)[keyof typeof SURFACES]

/**
 * SURFACE_KIND — 표면 계열 분류 (D-C2-S2-FUNNEL-COV 2계열 organic/audit).
 *
 * - organic = 본판정(노출·반복·클릭·미노출 적체) 집계 대상 표면.
 * - audit   = 점검 층 — 본판정에서 제외(적체 비제거·관찰자 효과 격리).
 *
 * 분류 정본 = D-C2-S2-FUNNEL-COV 결정 문언: `coverage_detail`=audit · 그 외 유기 표면
 * (`dashboard_eod`·`chain_sight`·`news_chip`)=organic. 분류는 디렉터 결정 사안 —
 * 미지 표면을 추측 분류하지 않는다.
 *
 * 완비 강제 2중: ⑴ `Record<Surface, …>` 타입 = 미분류 표면 추가 시 tsc FAIL(컴파일 타임)
 * ⑵ `__tests__/surfaces.guard.test.ts` 완비 가드(런타임·cast 우회 포착).
 */
export type SurfaceKind = 'organic' | 'audit'

export const SURFACE_KIND: Record<Surface, SurfaceKind> = {
  [SURFACES.DASHBOARD_EOD]: 'organic',
  [SURFACES.CHAIN_SIGHT]: 'organic',
  [SURFACES.NEWS_CHIP]: 'organic',
  [SURFACES.COVERAGE_DETAIL]: 'audit',
}
