/**
 * Coach API 클라이언트 — authAxios 경유, 타입 안전.
 *
 * 모든 호출은 `lib/api/authAxios`의 JWT 인터셉터 단일 소스를 거친다.
 * 직접 토큰을 다루지 않는다.
 */

import { authAxios } from '@/lib/api/authAxios'
import type { E1Request, E1Response, E2Request, E2Response } from './types'

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
