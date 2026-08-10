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
