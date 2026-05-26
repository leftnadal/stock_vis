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
//   summary / confidence / key_observations / metrics_table — 6 진입점 공통
//   action_items / risk_flags — E1, E3, E5 등
//   quoted_metrics — E2 (포트폴리오 종합 진단의 지표 인용)
// 향후 새 EP 필드는 본 합집합에 optional 추가 (graceful 미렌더 유지).
//
// 후속 검토: Slice 16 Part 5 후 C 리팩터링 재검토 (BaseCard + EP별 Section 분리).
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
  /** E2 quoted_metrics — 종합 진단이 인용한 핵심 지표 (free-form key→value). */
  quoted_metrics?: Record<string, unknown>
  /**
   * deprecated (#21, Slice 13+ 제거 예정). 컴포넌트는 미렌더.
   *
   * Slice 16 Part 2 §3 게이트: E3/E4/E5/E6 Output은 metrics_table 필드 자체가
   * 없음 (E1/E2만 default ""). optional로 완화 — 6 EP 모두 prop 전달 호환.
   */
  metrics_table?: string
}
