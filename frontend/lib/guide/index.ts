/**
 * 가이드 레지스트리 (D-GUIDE-TRACK).
 *
 * ⚠️ 이 데이터는 유저 가이드이자 야간 도그푸딩 에이전트의 채점 루브릭 단일 출처다.
 *    coreQuestion을 바꾸면 에이전트 평가 기준이 바뀐다.
 *
 * 새 화면 추가 = 도메인 파일에 GuideScreen 1건 등재 → 허브·오버레이 자동 반영(하드코딩 금지).
 */
import { CHAINSIGHT_GUIDE } from './chainsight';
import { DASHBOARD_GUIDE } from './dashboard';
import { MARKET_PULSE_GUIDE } from './marketPulse';
import { MONITOR_GUIDE } from './monitor';
import { PORTFOLIO_GUIDE } from './portfolio';
import type { GuideScreen } from './types';

export const GUIDE_SCREENS: GuideScreen[] = [
  ...DASHBOARD_GUIDE,
  ...MARKET_PULSE_GUIDE,
  ...CHAINSIGHT_GUIDE,
  ...MONITOR_GUIDE,
  ...PORTFOLIO_GUIDE,
];

/**
 * 라우트 → GuideScreen. 정확 일치만 인정한다.
 * (하위 경로 prefix 매칭 금지 — /monitor 가이드가 /monitor/new 에 새는 것을 막는다.)
 */
export function getGuideForRoute(pathname: string): GuideScreen | undefined {
  return GUIDE_SCREENS.find((s) => s.route === pathname);
}

export function getGuideById(id: string): GuideScreen | undefined {
  return GUIDE_SCREENS.find((s) => s.id === id);
}

export * from './types';
