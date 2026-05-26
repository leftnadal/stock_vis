/**
 * Coach API 클라이언트 — authAxios 경유, 타입 안전.
 *
 * 모든 호출은 `lib/api/authAxios`의 JWT 인터셉터 단일 소스를 거친다.
 * 직접 토큰을 다루지 않는다.
 */

import { authAxios } from '@/lib/api/authAxios'
import type {
  E1Request,
  E1Response,
  E2Request,
  E2Response,
  E3Request,
  E3Response,
  E4Request,
  E4Response,
  E5Request,
  E5Response,
  E6Request,
  E6Response,
} from './types'

// ── Endpoint 경로 상수 (Part 2+ 재사용) ──
export const COACH_E1_PATH = '/coach/e1/'
export const COACH_E2_PATH = '/coach/e2/'
export const COACH_E3_PATH = '/coach/e3/'
export const COACH_E4_PATH = '/coach/e4/'
export const COACH_E5_PATH = '/coach/e5/'
export const COACH_E6_PATH = '/coach/e6/'

/**
 * E1 GARP 진단 호출.
 *
 * authAxios의 baseURL은 `NEXT_PUBLIC_API_URL` (기본 `http://localhost:8000/api/v1`)
 * — 코드는 path만 신경쓰면 된다 (#19 회피).
 */
export async function postE1Coach(req: E1Request): Promise<E1Response> {
  const { data } = await authAxios.post<E1Response>(COACH_E1_PATH, req)
  return data
}

/**
 * E2 포트폴리오 종합 진단 호출.
 *
 * Slice 16 Part 1 — E1 패턴 복제. response는 봉투 `{output, llm_metadata, ...}`.
 */
export async function postE2Coach(req: E2Request): Promise<E2Response> {
  const { data } = await authAxios.post<E2Response>(COACH_E2_PATH, req)
  return data
}

/**
 * E3 집중도 분석 호출 — Slice 16 Part 3. E2/E6 패턴 복제.
 */
export async function postE3Coach(req: E3Request): Promise<E3Response> {
  const { data } = await authAxios.post<E3Response>(COACH_E3_PATH, req)
  return data
}

/**
 * E4 대화 Q&A 호출 — Slice 16 Part 5. 마지막 진입점.
 * 다른 EP와 달리 대화형 — `conversation_history`(이전 turns)를 누적 전달하고
 * `user_question`에는 신규 질문만 담는다. 응답 봉투 형태는 동형
 * `{output, llm_metadata}`. assistant turn append 시 content는 summary만 사용
 * (`E4Turn` 계약, types.ts 주석 참조).
 */
export async function postE4Coach(req: E4Request): Promise<E4Response> {
  const { data } = await authAxios.post<E4Response>(COACH_E4_PATH, req)
  return data
}

/**
 * E5 추출 진입점 (extraction_targets + time_series_context) 호출 — Slice 16 Part 4.
 * E3 패턴 복제. time_series_context는 codegen union(`number | string | null`) —
 * UI는 string 직렬화 권장(fixture 패턴).
 */
export async function postE5Coach(req: E5Request): Promise<E5Response> {
  const { data } = await authAxios.post<E5Response>(COACH_E5_PATH, req)
  return data
}

/**
 * E6 분석엔진 (비교 분석) 호출 — Slice 16 Part 2. E1/E2 패턴 복제.
 */
export async function postE6Coach(req: E6Request): Promise<E6Response> {
  const { data } = await authAxios.post<E6Response>(COACH_E6_PATH, req)
  return data
}
