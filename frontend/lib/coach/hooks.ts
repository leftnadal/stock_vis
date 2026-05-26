/**
 * Coach react-query 훅.
 *
 * E1은 "포트폴리오 제출 → LLM 진단" 사용자 행동·비용 행위라 `useMutation` 사용.
 * `useQuery`로 다루면 react-query가 자동 재요청·캐싱하려 들어 의도치 않은 LLM
 * 재호출·비용이 발생한다 (Part 1 §P1-C 결정 근거).
 *
 * 파일럿 단순성: 캐싱·재요청·중복 호출 dedup은 도입하지 않는다. 동일 포트폴리오
 * 재진단 캐싱은 추후 개선 후보.
 */

import { useMutation, type UseMutationResult } from '@tanstack/react-query'
import type { AxiosError } from 'axios'

import {
  postE1Coach,
  postE2Coach,
  postE3Coach,
  postE4Coach,
  postE5Coach,
  postE6Coach,
} from './api'
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

/**
 * E1 GARP 진단 mutation 훅.
 *
 * 반환:
 *   - `mutate(req)` / `mutateAsync(req)` — 호출 트리거
 *   - `data` — 성공 시 E1Response 봉투 ({output, llm_metadata, ...})
 *   - `error` — 실패 시 AxiosError
 *   - `isPending` / `isSuccess` / `isError` — 상태 플래그
 */
export function useE1Coach(): UseMutationResult<E1Response, AxiosError, E1Request> {
  return useMutation<E1Response, AxiosError, E1Request>({
    mutationFn: postE1Coach,
  })
}

/**
 * E2 포트폴리오 종합 진단 mutation 훅. E1 패턴 복제 (Slice 16 Part 1).
 */
export function useE2Coach(): UseMutationResult<E2Response, AxiosError, E2Request> {
  return useMutation<E2Response, AxiosError, E2Request>({
    mutationFn: postE2Coach,
  })
}

/**
 * E3 집중도 분석 mutation 훅. E2/E6 패턴 복제 (Slice 16 Part 3).
 */
export function useE3Coach(): UseMutationResult<E3Response, AxiosError, E3Request> {
  return useMutation<E3Response, AxiosError, E3Request>({
    mutationFn: postE3Coach,
  })
}

/**
 * E4 대화 Q&A mutation 훅. 마지막 진입점 (Slice 16 Part 5).
 *
 * 화면은 자체 useState로 turns를 누적 관리한다 — 본 훅은 단발 호출만 수행하고,
 * 매 호출은 신규 user_question + 누적된 conversation_history를 함께 전달.
 * 다른 EP와 달리 동일한 portfolio에 대해 연속 호출이 자연스러우므로 isSuccess
 * 상태 자체보다 `mutateAsync`의 반환값(또는 `onSuccess`)으로 turn append하는 패턴
 * 권장.
 */
export function useE4Coach(): UseMutationResult<E4Response, AxiosError, E4Request> {
  return useMutation<E4Response, AxiosError, E4Request>({
    mutationFn: postE4Coach,
  })
}

/**
 * E5 추출 진입점 mutation 훅. E3 패턴 복제 (Slice 16 Part 4).
 */
export function useE5Coach(): UseMutationResult<E5Response, AxiosError, E5Request> {
  return useMutation<E5Response, AxiosError, E5Request>({
    mutationFn: postE5Coach,
  })
}

/**
 * E6 분석엔진(비교 분석) mutation 훅. E2 패턴 복제 (Slice 16 Part 2).
 */
export function useE6Coach(): UseMutationResult<E6Response, AxiosError, E6Request> {
  return useMutation<E6Response, AxiosError, E6Request>({
    mutationFn: postE6Coach,
  })
}
