/**
 * 유저 가이드 데이터 계약 (D-GUIDE-TRACK, 2026-08-27)
 *
 * ⚠️ 이 데이터는 유저 가이드이자 야간 도그푸딩 에이전트의 채점 루브릭 단일 출처다.
 *    coreQuestion을 바꾸면 에이전트 평가 기준이 바뀐다.
 *
 * 별도 산문 가이드 문서를 만들지 않는다(복제 = drift). 문구 수정은 여기 한 곳.
 */

/** 서비스 플로우 5단계: 1 시장 흐름 파악 → 2 파급 발견 → 3 관심 추적 → 4 1차 검증 → 5 포트폴리오 반영 */
export type FlowStage = 1 | 2 | 3 | 4 | 5;

/** 병진 검수 전 = draft. draft → confirmed 전환은 검수 후 별도 슬라이스. */
export type GuideReviewStatus = 'draft' | 'confirmed';

export interface GuideRegion {
  /** 대상 요소의 data-guide 속성값. CSS 셀렉터 결합 금지(리팩터링 내성). */
  anchor: string;
  title: string;
  desc: string;
}

export interface GuideNextAction {
  label: string;
  route: string;
}

export interface GuideScreen {
  /** 화면 고유 id (예: "chainsight.main") */
  id: string;
  /** 오버레이가 붙을 라우트 (예: "/chainsight") */
  route: string;
  title: string;
  flowStage: FlowStage;
  /** "이 화면이 답하는 질문" — 에이전트 채점 루브릭의 기준 문장 */
  coreQuestion: string;
  /** "이 화면에서 알게 되는 것" 2~4개 */
  learnings: string[];
  regions: GuideRegion[];
  /** 플로우상 다음 행동 */
  nextAction?: GuideNextAction;
  reviewStatus: GuideReviewStatus;
}

export const FLOW_STAGE_LABELS: Record<FlowStage, string> = {
  1: '시장 흐름 파악',
  2: '파급 발견',
  3: '관심 추적',
  4: '1차 검증',
  5: '포트폴리오 반영',
};
