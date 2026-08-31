/**
 * RC-C-1 backbone 서비스 (authAxios — JWT 인터셉터 단일 소스, lib/api/authAxios.ts).
 * 자족 모듈(신규): 기존 chainsightService/chainsightPaths diff 최소화(4-1 행위보존).
 * NEXT_PUBLIC_API_URL 이 /api/v1 을 포함 → 경로는 /chainsight/ 부터.
 */

import { authAxios } from '@/lib/api/authAxios';
import type { BackboneResponse } from '@/types/backbone';

export const BACKBONE_PATH = '/chainsight/backbone/';

export async function fetchBackbone(limit = 20): Promise<BackboneResponse> {
  const { data } = await authAxios.get<BackboneResponse>(BACKBONE_PATH, {
    params: { limit },
  });
  return data;
}
