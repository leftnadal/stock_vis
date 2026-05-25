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

import { postE1Coach } from './api'
import type { E1Request, E1Response } from './types'

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
