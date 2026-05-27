/**
 * Coach 도메인 타입 alias 레이어 — 생성 타입(`api-types.ts`)의 유일한 진입점.
 *
 * 배경: openapi-typescript는 `COMPONENT_SPLIT_REQUEST: true` 설정 영향으로
 * request 컴포넌트에 "Request" 접미를 이중 부착한다 (`CoachE1RequestRequest`).
 * 화면·훅이 이런 거친 이름을 직접 참조하지 않도록 도메인 이름으로 정리.
 *
 * Slice 15는 E1만 화면화하지만 E2~E6도 같이 alias 해 두어 Slice 16+ 복제 시
 * 추가 작업 없이 import 가능 (Step 0의 "무료 이득" 정신 그대로).
 */

import type { components } from './api-types'

type Schemas = components['schemas']

// ── E1 ──
export type E1Request = Schemas['CoachE1RequestRequest']
export type E1Response = Schemas['CoachE1Response']

// ── E2 ──
export type E2Request = Schemas['CoachE2RequestRequest']
export type E2Response = Schemas['CoachE2Response']

// ── E3 ──
export type E3Request = Schemas['CoachE3RequestRequest']
export type E3Response = Schemas['CoachE3Response']

// ── E4 ──
export type E4Request = Schemas['CoachE4RequestRequest']
export type E4Response = Schemas['CoachE4Response']

/**
 * E4 conversation turn — P5-A 신규 정립 계약 (2026-05-26).
 *
 * 백엔드 CommentaryInputE4.conversation_history는 `list[dict[str, Any]]`로
 * 프론트가 형태를 정의한다. 표준은 `{role, content}` 2필드만 사용.
 *
 * - user turn content = 사용자 입력 질문 원문
 * - assistant turn content = E4Response.output.summary (요약만, key_observations 제외)
 *   → prompt 토큰 절약 + content 단일 문자열 단순성
 *
 * 인덱스 시그니처는 codegen `conversation_history: { [key: string]: unknown }[]`
 * 호환을 위한 구조 permission — 실제 turn은 role/content만 사용한다.
 */
export type E4Turn = {
  role: 'user' | 'assistant'
  content: string
  [key: string]: unknown
}

// ── E5 ──
export type E5Request = Schemas['CoachE5RequestRequest']
export type E5Response = Schemas['CoachE5Response']

/**
 * E5의 time_series_context는 codegen이 별도 component로 분리하지 않고 inline.
 * `_inline_pydantic_refs`(Pydantic↔spectacular bridge) 효과. 화면·테스트에서 nested
 * 객체를 직접 참조하려면 inline 경로(`E5Request['time_series_context']`)를 매번
 * 적기 부담스러우므로 NonNullable helper로 정리.
 * Slice 16 Part 4 사전 실측 결과 (2026-05-26).
 */
export type E5TimeSeriesContext = NonNullable<E5Request['time_series_context']>

// ── E6 ──
export type E6Request = Schemas['CoachE6RequestRequest']
export type E6Response = Schemas['CoachE6Response']

// ─────────────────────────────────────────────────────────────
// CommentaryCardData — 6 진입점(E1~E6) output의 공통 표시 모델.
//
// 배경: Slice 16 Part 1 §3 게이트 — 사용자 안 A 채택 (2026-05-26).
//   Slice 15는 CommentaryCard prop이 `E1Response['output']`로 lock돼 E2~E6
//   output을 직접 받지 못함. 6 진입점 output 필드의 합집합으로 일반화 →
//   한 컴포넌트가 모두 수용 + 진입점별 차이는 optional + graceful 미렌더로 분기.
//
// 필드 출처:
//   summary / confidence — 6 진입점 공통 (required)
//   key_observations — 6 진입점 공통 (optional, base 필드)
//   action_items — E1, E3, E5
//   risk_flags — E1, E3, E6
//   quoted_metrics — E2, E5, E6 (지표 인용)
// 향후 새 EP 필드는 본 합집합에 optional 추가 (graceful 미렌더 유지).
//
// Slice 17 분할 완료: BaseCard + Key/Action/Quoted/RiskFlags Section. CommentaryCard
// 는 순수 조립부. ⚠ 안 B 경계 규칙 — 외형 wrapper(BaseCard / 말풍선)는 비공유.
//
// Slice 17 Closing C-A: deprecated metrics_table 필드 프론트 제거 (#21 부분 close).
// 백엔드 스키마는 잔여 — codegen `CoachE1Response.output.metrics_table` required
// 그대로. structural typing으로 mutation.data.output → CommentaryCardData 전달 시
// extra prop 허용되어 호환 유지.
// ─────────────────────────────────────────────────────────────

export type CommentaryConfidence = 'high' | 'medium' | 'low'
export type CommentaryActionPriority = 'high' | 'medium' | 'low'
export type CommentaryActionCategory = 'rebalance' | 'review' | 'monitor' | 'research'

export interface CommentaryActionItem {
  title: string
  description: string
  priority: CommentaryActionPriority
  category: CommentaryActionCategory | null
}

export interface CommentaryCardData {
  summary: string
  confidence: CommentaryConfidence
  key_observations?: string[]
  action_items?: CommentaryActionItem[]
  risk_flags?: string[]
  /** E2·E5·E6 quoted_metrics — 종합 진단이 인용한 핵심 지표 (free-form key→value). */
  quoted_metrics?: Record<string, unknown>
}
