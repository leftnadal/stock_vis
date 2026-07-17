/**
 * Chain Sight API 경로 단일 소스 (FE↔BE 계약).
 *
 * ⑳-E: ego 경로가 BE 라우트(`ego/<symbol>/`, apps/chain_sight/api/urls.py:36)와
 * 어긋나 `/chainsight/<sym>/ego/`로 404 미검증 이월된 사건(common-bugs #57) 재발 방지.
 * ego 요청 경로는 반드시 이 헬퍼로만 생성한다(하드코딩 산재 금지).
 *
 * 계약 테스트:
 *  - FE: frontend/__tests__/chainsight/chainsightPaths.test.ts (경로 문자열 검증)
 *  - BE: tests/chainsight/test_ego_api.py (동일 경로가 EgoGraphView로 resolve)
 */

/**
 * PG 네이티브 ego 그래프 경로.
 * BE 라우트: path("ego/<str:symbol>/", EgoGraphView) → /api/v1/chainsight/ego/<SYM>/
 * (authAxios base = NEXT_PUBLIC_API_URL 이 /api/v1 을 이미 포함하므로 여기선 /chainsight/ 부터.)
 */
export const egoPath = (symbol: string): string =>
  `/chainsight/ego/${symbol.toUpperCase()}/`;
