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

// ── E6 ──
export type E6Request = Schemas['CoachE6RequestRequest']
export type E6Response = Schemas['CoachE6Response']
