/**
 * FE↔BE ego 경로 계약 테스트 (⑳-E S1).
 *
 * common-bugs #57: fetchEgo가 `/chainsight/<sym>/ego/`(구 패턴)를 호출해 BE 라우트
 * `ego/<sym>/`와 어긋나 404가 미검증 이월됨. 이 테스트는 FE가 생성하는 경로가
 * BE 라우트 패턴(고정 프리픽스 `ego/`)과 일치함을 못박는다.
 *
 * 짝: tests/chainsight/test_ego_api.py::test_ego_route_contract (동일 경로 BE resolve).
 */

import { describe, it, expect } from 'vitest';
import { egoPath } from '@/services/chainsightPaths';

describe('ego 경로 계약 (FE↔BE)', () => {
  it('BE 라우트와 일치하는 고정 프리픽스 ego/ 를 생성한다', () => {
    // BE: path("ego/<str:symbol>/") → /api/v1/chainsight/ego/<SYM>/
    // authAxios base(NEXT_PUBLIC_API_URL)가 /api/v1 포함 → 여기선 /chainsight/ 부터.
    expect(egoPath('NVDA')).toBe('/chainsight/ego/NVDA/');
  });

  it('심볼을 대문자로 정규화한다', () => {
    expect(egoPath('nvda')).toBe('/chainsight/ego/NVDA/');
    expect(egoPath('aApL')).toBe('/chainsight/ego/AAPL/');
  });

  it('구 404 패턴 `<sym>/ego/` 을 재도입하지 않는다 (회귀 가드)', () => {
    // 프리픽스가 심볼보다 앞(ego/<SYM>/), 심볼 뒤(/<SYM>/ego/)가 아님.
    expect(egoPath('NVDA')).not.toMatch(/\/NVDA\/ego\/$/);
    expect(egoPath('NVDA')).toMatch(/\/chainsight\/ego\/NVDA\/$/);
  });
});
